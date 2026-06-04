"""Background guardian that blocks locked application launches."""
from __future__ import annotations

import contextlib
import os
import signal
from pathlib import Path
from typing import Iterable, Optional

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QWidget

from src.facelock.auth import launch_auth
from src.facelock.database import db


def _normalize_token(value: str) -> str:
    value = (value or "").strip().lower()
    if not value:
        return ""
    return Path(value).name


def _process_cmdline(pid: int) -> list[str]:
    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return []
    if not raw:
        return []
    parts = [part.decode("utf-8", errors="ignore") for part in raw.split(b"\0") if part]
    return parts


def _process_exe(pid: int) -> str:
    try:
        return os.path.realpath(f"/proc/{pid}/exe")
    except OSError:
        return ""


class AppLaunchGuardian(QObject):
    def __init__(self, parent: Optional[QWidget] = None, db_path: Optional[str] = None, interval_ms: int = 1500) -> None:
        super().__init__(parent)
        self.db_path = db_path
        self._handled_pids: set[int] = set()
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.poll)
        self._timer.start()

    def _locked_apps(self) -> list[dict]:
        return [row for row in db.list_locked_apps(self.db_path) if row.get("locked")]

    def _process_identity_tokens(self, pid: int, cmdline: list[str]) -> set[str]:
        tokens = {str(pid)}
        if cmdline:
            tokens.add(cmdline[0])
            tokens.add(_normalize_token(cmdline[0]))
        exe = _process_exe(pid)
        if exe:
            tokens.add(exe)
            tokens.add(_normalize_token(exe))
        return {token for token in tokens if token}

    def _app_identity_tokens(self, app: dict) -> set[str]:
        tokens = set()
        for value in (app.get("desktop_file"), app.get("exec"), app.get("name")):
            if not value:
                continue
            value = str(value)
            tokens.add(value)
            tokens.add(_normalize_token(value))
        return {token for token in tokens if token}

    def _matches_locked_app(self, pid: int, cmdline: list[str], app: dict) -> bool:
        process_tokens = self._process_identity_tokens(pid, cmdline)
        app_tokens = self._app_identity_tokens(app)
        return bool(process_tokens.intersection(app_tokens))

    def _iter_processes(self) -> Iterable[dict]:
        proc_root = Path("/proc")
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid == os.getpid():
                continue
            cmdline = _process_cmdline(pid)
            if not cmdline:
                continue
            yield {"pid": pid, "cmdline": cmdline}

    def poll(self) -> None:
        locked_apps = self._locked_apps()
        if not locked_apps:
            return

        for process in self._iter_processes():
            pid = int(process["pid"])
            if pid in self._handled_pids:
                continue

            cmdline = list(process["cmdline"])
            match = next((app for app in locked_apps if self._matches_locked_app(pid, cmdline, app)), None)
            if match is None:
                continue

            self._handled_pids.add(pid)
            self._handle_locked_launch(pid, match)

    def _handle_locked_launch(self, pid: int, app: dict) -> None:
        app_name = app.get("name") or app.get("exec") or "Locked application"
        try:
            os.kill(pid, signal.SIGSTOP)
        except ProcessLookupError:
            return
        except PermissionError:
            return

        parent_obj = self.parent()
        parent_widget = parent_obj if isinstance(parent_obj, QWidget) else None
        allowed, method = launch_auth.authenticate_locked_launch(
            app_name=str(app_name),
            parent=parent_widget,
            db_path=self.db_path,
        )
        if allowed:
            db.add_access_log(str(app_name), "allowed", note=f"authenticated via {method}", db_path=self.db_path)
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGCONT)
            return

        db.add_access_log(str(app_name), "denied", note="authentication failed", db_path=self.db_path)
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)