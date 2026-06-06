#!/usr/bin/env python3
"""OwlLock control panel — shown when clicking the desktop entry.

Checks the background guardian status and provides quick actions.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ensure we can import from src/
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.facelock.gui.theme import apply_theme  # noqa: E402

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtGui import QIcon, QPixmap  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

SERVICE_NAME = "owllock.service"
ROOT_DIR = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT_DIR / "assests" / "logo.png"


def _logo_pixmap(size: int = 64) -> QPixmap:
    pixmap = QPixmap(str(LOGO_PATH))
    if pixmap.isNull():
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def _service_running() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", SERVICE_NAME],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def _start_service() -> bool:
    try:
        result = subprocess.run(
            ["systemctl", "--user", "start", SERVICE_NAME],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _open_gui() -> None:
    # Try the pip-installed console entry first
    owllock_bin = ROOT_DIR / ".venv" / "bin" / "owllock"
    if owllock_bin.exists():
        subprocess.Popen(
            [str(owllock_bin)],
            cwd=str(ROOT_DIR),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return
    # Fallback: run via python -m
    for py in (ROOT_DIR / ".venv" / "bin" / "python3", Path(sys.executable)):
        if py.exists():
            subprocess.Popen(
                [str(py), "-m", "src.facelock.app"],
                cwd=str(ROOT_DIR),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            return


class OwlLockCtl(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("OwlLock")
        self.setWindowIcon(QIcon(_logo_pixmap(128)))
        self.setFixedSize(380, 220)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog { background: #0d1424; color: #e7efff; }
            QLabel#Title { font-size: 20px; font-weight: 700; background: transparent; }
            QLabel#Status { font-size: 14px; background: transparent; }
            QPushButton {
                background: #2f77ff; border: none; color: white;
                border-radius: 10px; padding: 10px 16px; font-weight: 600;
            }
            QPushButton:hover { background: #4384ff; }
            QPushButton#Secondary {
                background: #1a2a46; color: #e7efff;
            }
            QPushButton#Secondary:hover { background: #233758; }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setFixedSize(48, 48)
        logo.setPixmap(_logo_pixmap(48))
        header.addWidget(logo)

        title = QLabel("OwlLock")
        title.setObjectName("Title")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        running = _service_running()
        self.status_label = QLabel(
            f"Guardian is {'active' if running else 'inactive'}"
        )
        self.status_label.setObjectName("Status")
        self.status_label.setStyleSheet(
            f"color: {'#4ade80' if running else '#e54848'}; background: transparent;"
        )
        root.addWidget(self.status_label)

        if not running:
            hint = QLabel("Apps will NOT be locked until the guardian is running.")
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #90a7d3; background: transparent;")
            root.addWidget(hint)

        root.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()

        if not running:
            start_btn = QPushButton("Start Guardian")
            start_btn.clicked.connect(self._start)
            actions.addWidget(start_btn)

        gui_btn = QPushButton("Open Settings")
        gui_btn.clicked.connect(self._open_gui)
        actions.addWidget(gui_btn)

        close_btn = QPushButton("Close")
        close_btn.setObjectName("Secondary")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(close_btn)

        root.addLayout(actions)

    def _start(self) -> None:
        if _start_service():
            self.status_label.setText("Guardian is active")
            self.status_label.setStyleSheet("color: #4ade80; background: transparent;")
        else:
            QMessageBox.warning(self, "OwlLock", "Could not start the guardian service.")

    def _open_gui(self) -> None:
        _open_gui()
        self.accept()


def main() -> int:
    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    dialog = OwlLockCtl()
    return 0 if dialog.exec() == QDialog.DialogCode.Accepted else 1


if __name__ == "__main__":
    raise SystemExit(main())
