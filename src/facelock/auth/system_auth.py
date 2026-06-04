"""System password gate for FaceLock startup."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


ROOT_DIR = Path(__file__).resolve().parents[3]
LOGO_PATH = ROOT_DIR / "assests" / "logo.png"


def _logo_pixmap(size: int = 72) -> QPixmap:
    pixmap = QPixmap(str(LOGO_PATH))
    if pixmap.isNull():
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


class PasswordPrompt(QDialog):
    def __init__(self, parent: Optional[QWidget] = None, message: str = "Enter your laptop password to open OwlLock.") -> None:
        super().__init__(parent)
        self.setWindowTitle("OwlLock")
        self.setWindowIcon(QIcon(_logo_pixmap(128)))
        self.setModal(True)
        self.setFixedWidth(420)
        self.setStyleSheet(
            """
            QDialog {
                background: #0d1424;
                color: #e7efff;
            }
            QLabel#Title {
                font-size: 20px;
                font-weight: 700;
                background: transparent;
            }
            QLabel#Subtitle {
                color: #90a7d3;
                background: transparent;
            }
            QLineEdit {
                background: #0e1728;
                border: 1px solid #263d63;
                border-radius: 12px;
                padding: 12px 14px;
                color: #e7efff;
                font-size: 13px;
            }
            QPushButton {
                background: #2f77ff;
                border: none;
                color: white;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 600;
                min-width: 90px;
            }
            QPushButton:hover {
                background: #4384ff;
            }
            QPushButton#CancelButton {
                background: #1a2a46;
                color: #e7efff;
            }
            QPushButton#CancelButton:hover {
                background: #233758;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)

        header = QHBoxLayout()
        logo = QLabel()
        logo.setFixedSize(64, 64)
        logo.setPixmap(_logo_pixmap(64))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(logo)

        text_block = QVBoxLayout()
        title = QLabel("OwlLock")
        title.setObjectName("Title")
        subtitle = QLabel(message)
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        title.setStyleSheet("background: transparent;")
        subtitle.setStyleSheet("background: transparent;")
        text_block.addWidget(title)
        text_block.addWidget(subtitle)
        header.addLayout(text_block, 1)

        outer.addLayout(header)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Laptop password")
        outer.addWidget(self.password_input)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        cancel.setObjectName("CancelButton")
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)

        ok = QPushButton("Open")
        ok.clicked.connect(self.accept)
        actions.addWidget(ok)
        outer.addLayout(actions)

    def password(self) -> str:
        return self.password_input.text()


def require_system_password(parent: Optional[QWidget] = None, message: str = "Enter your laptop password to open OwlLock.") -> bool:
    """Prompt for the user's laptop password and verify it with sudo.

    The password is not stored. It is only passed to `sudo -S -v` to verify
    the current user can authenticate the session.
    """
    if shutil.which("sudo") is None:
        QMessageBox.critical(parent, "FaceLock", "sudo is not available on this system.")
        return False

    dialog = PasswordPrompt(parent, message=message)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False
    password = dialog.password()
    if not password:
        return False

    result = subprocess.run(
        ["sudo", "-k", "-S", "-v", "-p", ""],
        input=password + "\n",
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "Authentication failed.").strip()
        QMessageBox.warning(parent, "FaceLock", message)
        return False
    return True
