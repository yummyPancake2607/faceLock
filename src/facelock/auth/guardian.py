"""Background guardian that blocks locked application launches."""
from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Optional

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QWidget

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
    def __init__(self, parent: Optional[QWidget] = None, db_path: Optional[str] = None, interval_ms: int = 200) -> None:
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

        processes = list(self._iter_processes())
        print(f"[owllock] poll: {len(processes)} processes, {len(locked_apps)} locked apps",
              file=sys.stderr)

        for process in processes:
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
        print(f"[owllock] locked launch detected: pid={pid} app={app_name}", file=sys.stderr)
        try:
            os.kill(pid, signal.SIGSTOP)
        except ProcessLookupError:
            print(f"[owllock] pid {pid} vanished before SIGSTOP", file=sys.stderr)
            return
        except PermissionError:
            print(f"[owllock] permission denied SIGSTOP pid {pid}", file=sys.stderr)
            return

        print(f"[owllock] SIGSTOP'd pid {pid}, spawning auth-prompt", file=sys.stderr)
        method = self._run_auth_prompt(str(app_name))

        if method:
            print(f"[owllock] auth succeeded for '{app_name}' via {method}, SIGCONT pid {pid}",
                  file=sys.stderr)
            db.add_access_log(str(app_name), "allowed", note=f"authenticated via {method}", db_path=self.db_path)
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.kill(pid, signal.SIGCONT)
            return

        print(f"[owllock] auth failed for '{app_name}', SIGKILL pid {pid}", file=sys.stderr)
        db.add_access_log(str(app_name), "denied", note="authentication failed", db_path=self.db_path)
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)

    def _run_auth_prompt(self, app_name: str) -> str | None:
        """Spawn the auth dialog in a separate process with the user's display."""
        project_root = Path(__file__).resolve().parents[3]
        script = project_root / "scripts" / "auth-prompt.py"
        python = project_root / ".venv" / "bin" / "python3"

        if not script.exists() or not python.exists():
            python_bin = sys.executable
        else:
            python_bin = str(python)

        cmd = [python_bin, str(script), app_name]
        if self.db_path:
            cmd += ["--db", self.db_path]

        # Pass display env vars but strip offscreen so the dialog is visible
        env = os.environ.copy()
        env.pop("QT_QPA_PLATFORM", None)
        env.pop("QT_QPA_PLATFORMTHEME", None)

        print(f"[owllock] spawning auth-prompt for '{app_name}': {' '.join(cmd)}",
              file=sys.stderr)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )
        except subprocess.TimeoutExpired:
            print(f"[owllock] auth-prompt timed out for '{app_name}'", file=sys.stderr)
            return None
        except FileNotFoundError as exc:
            print(f"[owllock] auth-prompt binary not found for '{app_name}': {exc}",
                  file=sys.stderr)
            return None

        if result.returncode == 0:
            method = result.stdout.strip()
            if method in ("face", "password"):
                print(f"[owllock] auth-prompt succeeded for '{app_name}': {method}",
                      file=sys.stderr)
                return method
            print(f"[owllock] auth-prompt returned unknown method '{method}' for '{app_name}'",
                  file=sys.stderr)
            return None

        print(f"[owllock] auth-prompt failed (rc={result.returncode}) for '{app_name}':",
              file=sys.stderr)
        if result.stderr:
            for line in result.stderr.strip().splitlines():
                print(f"[owllock]   {line}", file=sys.stderr)
        return None