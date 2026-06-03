"""Modern OwlLock main window."""
from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable, Optional

import cv2
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.facelock.auth.system_auth import require_system_password
from src.facelock.database import db
from src.facelock.gui.face_enrollment import FaceEnrollmentDialog
from src.facelock.services import app_scanner


APP_TITLE = "OwlLock"
ROOT_DIR = Path(__file__).resolve().parents[3]
LOGO_PATH = ROOT_DIR / "assests" / "logo.png"


def _apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget {
            background: #0d1424;
            color: #e7efff;
            font-size: 13px;
        }
        QFrame#ShellCard, QFrame#AppCard, QFrame#HeroCard, QFrame#FaceCard, QFrame#PanelCard {
            background: #101a2f;
            border: 1px solid #203455;
            border-radius: 16px;
        }
        QLabel#Title {
            font-size: 30px;
            font-weight: 700;
            background: transparent;
        }
        QLabel#SectionTitle {
            font-size: 18px;
            font-weight: 700;
            background: transparent;
        }
        QLabel#Subtitle, QLabel#Muted {
            color: #90a7d3;
            background: transparent;
        }
        QLineEdit {
            background: #0e1728;
            border: 1px solid #263d63;
            border-radius: 10px;
            padding: 10px 12px;
            color: #e7efff;
        }
        QPushButton {
            background: #2f77ff;
            border: none;
            color: white;
            border-radius: 10px;
            padding: 10px 14px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #4384ff;
        }
        QPushButton[secondary="true"] {
            background: #1a2a46;
            color: #e7efff;
        }
        QPushButton[secondary="true"]:hover {
            background: #233758;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QListWidget {
            background: #0e1728;
            border: 1px solid #263d63;
            border-radius: 12px;
            padding: 6px;
        }
        QListWidget::item {
            padding: 8px 10px;
            border-radius: 8px;
        }
        QListWidget::item:selected {
            background: #2f77ff;
            color: white;
        }
        QPushButton#LockButton {
            background: #2f77ff;
            color: white;
        }
        QPushButton#UnlockButton {
            background: #e54848;
            color: white;
        }
        """
    )


def _load_logo_pixmap(size: int) -> QPixmap:
    pixmap = QPixmap(str(LOGO_PATH))
    if pixmap.isNull():
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def _load_logo_icon() -> QIcon:
    pixmap = _load_logo_pixmap(256)
    return QIcon(pixmap)


def _icon_for_app(app: dict) -> QIcon:
    icon_value = (app.get("icon") or "").strip()
    if not icon_value:
        return QIcon.fromTheme("application-x-executable")
    if os.path.exists(icon_value):
        return QIcon(icon_value)
    themed = QIcon.fromTheme(icon_value)
    if not themed.isNull():
        return themed
    return QIcon.fromTheme("application-x-executable")


def _scaled_icon_pixmap(app: dict, size: int = 48) -> QPixmap:
    icon = _icon_for_app(app)
    pixmap = icon.pixmap(QSize(size, size))
    if pixmap.isNull():
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
    return pixmap


@dataclass
class AppRecord:
    app: dict
    registered: bool = False
    locked: bool = False


class AppCard(QFrame):
    def __init__(self, record: AppRecord, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.record = record
        self.db_path = db_path
        self.app = record.app
        self.setObjectName("AppCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        icon = QLabel()
        icon.setFixedSize(80, 80)
        icon.setPixmap(_scaled_icon_pixmap(self.app, 80))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(icon, 0, Qt.AlignmentFlag.AlignLeft)

        name = QLabel(self.app.get("name", "Unknown App"))
        name.setObjectName("SectionTitle")
        name.setWordWrap(True)
        outer.addWidget(name)

        self.toggle_button = QPushButton()
        self.toggle_button.clicked.connect(self.toggle_lock)
        outer.addWidget(self.toggle_button)

        self.refresh_state(record.registered, record.locked)

    def refresh_state(self, registered: bool, locked: bool) -> None:
        self.record.registered = registered
        self.record.locked = locked
        if locked:
            self.toggle_button.setText("Unlock")
            self.toggle_button.setObjectName("UnlockButton")
            self.toggle_button.style().unpolish(self.toggle_button)
            self.toggle_button.style().polish(self.toggle_button)
        elif registered:
            self.toggle_button.setText("Lock")
            self.toggle_button.setObjectName("LockButton")
            self.toggle_button.style().unpolish(self.toggle_button)
            self.toggle_button.style().polish(self.toggle_button)
        else:
            self.toggle_button.setText("Lock")
            self.toggle_button.setObjectName("LockButton")
            self.toggle_button.style().unpolish(self.toggle_button)
            self.toggle_button.style().polish(self.toggle_button)

    def register_app(self) -> None:
        db.upsert_locked_app(
            name=self.app.get("name", ""),
            exec_cmd=self.app.get("exec", ""),
            icon=self.app.get("icon"),
            desktop_file=self.app.get("desktop_file"),
            locked=False,
            db_path=self.db_path,
        )
        self.refresh_state(True, False)

    def toggle_lock(self) -> None:
        if self.record.locked:
            db.set_locked_by_identity(
                name=self.app.get("name"),
                exec_cmd=self.app.get("exec"),
                desktop_file=self.app.get("desktop_file"),
                locked=False,
                db_path=self.db_path,
            )
            self.refresh_state(True, False)
            return
        db.upsert_locked_app(
            name=self.app.get("name", ""),
            exec_cmd=self.app.get("exec", ""),
            icon=self.app.get("icon"),
            desktop_file=self.app.get("desktop_file"),
            locked=True,
            db_path=self.db_path,
        )
        self.refresh_state(True, True)


class ApplicationsPanel(QFrame):
    def __init__(self, scan_paths: Optional[Iterable[str]] = None, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.setObjectName("ShellCard")
        self.scan_paths = scan_paths
        self.db_path = db_path
        self.apps: list[dict] = []
        self.cards: list[AppCard] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        heading = QVBoxLayout()
        title = QLabel("Applications")
        title.setObjectName("Title")
        heading.addWidget(title)
        outer.addLayout(heading)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search applications")
        self.search.textChanged.connect(self.apply_filter)
        search_row.addWidget(self.search, 1)

        self.scan_button = QPushButton("Scan Apps")
        self.scan_button.setProperty("secondary", True)
        self.scan_button.clicked.connect(self.refresh)
        search_row.addWidget(self.scan_button)

        outer.addLayout(search_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_host = QWidget()
        self.cards_layout = QGridLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setHorizontalSpacing(12)
        self.cards_layout.setVerticalSpacing(12)
        self.scroll.setWidget(self.cards_host)
        outer.addWidget(self.scroll, 1)

        self.refresh()

    def _identity(self, app: dict) -> str:
        return app.get("desktop_file") or app.get("exec") or app.get("name") or ""

    def _locked_index(self, locked_rows: list[dict]) -> dict[str, dict]:
        index: dict[str, dict] = {}
        for row in locked_rows:
            for value in (row.get("desktop_file"), row.get("exec"), row.get("name")):
                if value:
                    index[value] = row
        return index

    def _clear_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards = []

    def refresh(self) -> None:
        locked_index = self._locked_index(db.list_locked_apps(self.db_path))
        self.apps = app_scanner.scan_applications(self.scan_paths)

        self._clear_cards()
        columns = 2
        for index, app in enumerate(self.apps):
            identity = self._identity(app)
            locked_row = locked_index.get(identity)
            record = AppRecord(app=app, registered=locked_row is not None, locked=bool(locked_row and locked_row.get("locked")))
            card = AppCard(record, db_path=self.db_path)
            self.cards.append(card)
            row = index // columns
            col = index % columns
            self.cards_layout.addWidget(card, row, col)

        for col in range(columns):
            self.cards_layout.setColumnStretch(col, 1)
        self.apply_filter(self.search.text())

    def apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for card in self.cards:
            app = card.app
            haystack = " ".join(
                [
                    app.get("name", ""),
                    app.get("exec", ""),
                    app.get("exec_raw", ""),
                    app.get("desktop_file", ""),
                    " ".join(app.get("categories", [])),
                ]
            ).lower()
            card.setVisible(not needle or needle in haystack)

    def _selected_cards(self) -> list[AppCard]:
        return []


class FaceRegistrationPanel(QFrame):
    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.setObjectName("FaceCard")
        self.db_path = db_path

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        title = QLabel("Face Registration")
        title.setObjectName("SectionTitle")
        outer.addWidget(title)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Face profile label")
        outer.addWidget(self.name_input)

        buttons = QHBoxLayout()
        self.register_face_button = QPushButton("Register Face")
        self.register_face_button.setObjectName("PrimaryAction")
        self.register_face_button.clicked.connect(self.register_face)
        buttons.addWidget(self.register_face_button)

        self.refresh_button = QPushButton("Refresh Stored Faces")
        self.refresh_button.setProperty("secondary", True)
        self.refresh_button.clicked.connect(self.refresh_status)
        buttons.addWidget(self.refresh_button)
        buttons.addStretch(1)
        outer.addLayout(buttons)

    def refresh_status(self) -> None:
        return

    def register_face(self) -> None:
        label = self.name_input.text().strip()
        if not label:
            label = os.environ.get("USER") or os.environ.get("USERNAME") or "default"

        dialog = FaceEnrollmentDialog(label=label, db_path=self.db_path, parent=self)
        dialog.exec()


class ProfileManagerPanel(QFrame):
    def __init__(self, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.setObjectName("PanelCard")
        self.db_path = db_path

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(10)

        title = QLabel("Face Profiles")
        title.setObjectName("SectionTitle")
        outer.addWidget(title)

        self.list = QListWidget()
        outer.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setProperty("secondary", True)
        self.refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(self.refresh_button)

        self.delete_button = QPushButton("Delete Profile")
        self.delete_button.setProperty("secondary", True)
        self.delete_button.clicked.connect(self.delete_selected)
        buttons.addWidget(self.delete_button)
        outer.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        users = db.list_users(self.db_path)
        for row in users:
            item = QListWidgetItem(row["label"])
            item.setData(Qt.ItemDataRole.UserRole, row["label"])
            self.list.addItem(item)

    def delete_selected(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        label = item.data(Qt.ItemDataRole.UserRole)
        if not label:
            return
        confirm = QMessageBox.question(
            self,
            "FaceLock",
            f"Delete profile '{label}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        db.delete_user_by_label(label, self.db_path)
        self.refresh()


class FaceLockWindow(QMainWindow):
    def __init__(self, scan_paths: Optional[Iterable[str]] = None, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.scan_paths = scan_paths
        self.db_path = db_path
        self.setWindowTitle(APP_TITLE)
        self.resize(1440, 900)
        self.setWindowIcon(_load_logo_icon())

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(16)

        instruction = QLabel("Select the application to lock")
        instruction.setObjectName("SectionTitle")
        instruction.setAlignment(Qt.AlignmentFlag.AlignLeft)
        root_layout.addWidget(instruction)

        content = QHBoxLayout()
        content.setSpacing(16)

        self.apps_panel = ApplicationsPanel(scan_paths=scan_paths, db_path=db_path)
        content.addWidget(self.apps_panel, 3)

        sidebar = QVBoxLayout()
        sidebar.setSpacing(16)

        self.face_panel = FaceRegistrationPanel(db_path=db_path)
        sidebar.addWidget(self.face_panel)

        self.profile_panel = ProfileManagerPanel(db_path=db_path)
        sidebar.addWidget(self.profile_panel, 1)

        content.addLayout(sidebar, 1)
        root_layout.addLayout(content, 1)

        self.setCentralWidget(root)

    def refresh_all(self) -> None:
        self.apps_panel.refresh()
        self.profile_panel.refresh()


def build_app(scan_paths: Optional[Iterable[str]] = None, db_path: Optional[str] = None) -> tuple[QApplication, FaceLockWindow]:
    app = QApplication.instance() or QApplication([])
    app.setApplicationName(APP_TITLE)
    app.setWindowIcon(_load_logo_icon())
    _apply_theme(app)
    window = FaceLockWindow(scan_paths=scan_paths, db_path=db_path)
    return app, window
