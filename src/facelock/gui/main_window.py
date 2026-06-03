"""Main FaceLock GUI window."""
from __future__ import annotations

import os
from typing import Iterable, Optional

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.facelock.database import db
from src.facelock.services import app_scanner


def _apply_dark_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QMainWindow, QWidget {
            background: #111318;
            color: #e6e9ef;
            font-size: 12px;
        }
        QFrame#Panel {
            background: #171b22;
            border: 1px solid #2a3140;
            border-radius: 12px;
        }
        QTableWidget {
            background: #131720;
            border: 1px solid #2a3140;
            gridline-color: #2a3140;
            selection-background-color: #2f6fed;
            selection-color: white;
            alternate-background-color: #151a24;
        }
        QHeaderView::section {
            background: #1b2130;
            color: #cfd6e6;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #2a3140;
        }
        QPushButton {
            background: #2f6fed;
            border: none;
            color: white;
            padding: 9px 14px;
            border-radius: 8px;
            font-weight: 600;
        }
        QPushButton:hover {
            background: #3f7bff;
        }
        QPushButton:disabled {
            background: #3b4252;
            color: #9aa4b2;
        }
        QLabel#Title {
            font-size: 24px;
            font-weight: 700;
        }
        QLabel#Subtitle {
            color: #a9b3c7;
        }
        QLineEdit {
            background: #131720;
            border: 1px solid #2a3140;
            border-radius: 8px;
            padding: 8px 10px;
            color: #e6e9ef;
        }
        """
    )


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


class ApplicationsTab(QWidget):
    def __init__(self, scan_paths: Optional[Iterable[str]] = None, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.scan_paths = scan_paths
        self.db_path = db_path
        self.apps = []
        self.search_text = ""

        layout = QVBoxLayout(self)

        header = QFrame()
        header.setObjectName("Panel")
        header_layout = QVBoxLayout(header)
        title = QLabel("Installed Applications")
        title.setObjectName("Title")
        subtitle = QLabel("Search, register, and lock apps discovered from your desktop entries.")
        subtitle.setObjectName("Subtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search apps, exec names, categories...")
        header_layout.addWidget(self.search)
        layout.addWidget(header)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["App", "Exec", "Status"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setIconSize(QSize(32, 32))
        layout.addWidget(self.table)

        button_row = QHBoxLayout()
        self.refresh_button = QPushButton("Scan Apps")
        self.register_button = QPushButton("Register Selected")
        self.lock_button = QPushButton("Lock Selected")
        self.unlock_button = QPushButton("Unlock Selected")
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.register_button)
        button_row.addWidget(self.lock_button)
        button_row.addWidget(self.unlock_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.refresh_button.clicked.connect(self.refresh)
        self.register_button.clicked.connect(self.register_selected)
        self.lock_button.clicked.connect(self.lock_selected)
        self.unlock_button.clicked.connect(self.unlock_selected)
        self.search.textChanged.connect(self.apply_filter)

        self.refresh()

    def refresh(self) -> None:
        locked_rows = db.list_locked_apps(self.db_path)
        locked_index = self._locked_index(locked_rows)
        self.apps = app_scanner.scan_applications(self.scan_paths)

        self.table.setRowCount(len(self.apps))
        for row, app in enumerate(self.apps):
            identity = self._identity(app)
            status = "Locked" if identity in locked_index and locked_index[identity].get("locked", False) else "Available"

            name_item = QTableWidgetItem(app.get("name", ""))
            name_item.setIcon(_icon_for_app(app))
            name_item.setToolTip(app.get("desktop_file") or "")
            name_item.setData(Qt.ItemDataRole.UserRole, app)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            exec_item = QTableWidgetItem(app.get("exec", ""))
            exec_item.setToolTip(app.get("exec_raw") or app.get("exec") or "")
            exec_item.setFlags(exec_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, exec_item)
            self.table.setItem(row, 2, status_item)

        self.apply_filter(self.search.text())

    def _identity(self, app: dict) -> str:
        return app.get("desktop_file") or app.get("exec") or app.get("name") or ""

    def _locked_index(self, locked_rows: list[dict]) -> dict[str, dict]:
        index: dict[str, dict] = {}
        for row in locked_rows:
            for value in (row.get("desktop_file"), row.get("exec"), row.get("name")):
                if value:
                    index[value] = row
        return index

    def apply_filter(self, text: str) -> None:
        self.search_text = text.strip().lower()
        for row, app in enumerate(self.apps):
            haystack = " ".join(
                [
                    app.get("name", ""),
                    app.get("exec", ""),
                    app.get("exec_raw", ""),
                    app.get("desktop_file", ""),
                    " ".join(app.get("categories", [])),
                ]
            ).lower()
            self.table.setRowHidden(row, bool(self.search_text and self.search_text not in haystack))

    def _selected_apps(self) -> list[dict]:
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows() if not self.table.isRowHidden(index.row())})
        return [self.apps[row] for row in rows if 0 <= row < len(self.apps)]

    def register_selected(self) -> None:
        selected = self._selected_apps()
        if not selected:
            QMessageBox.information(self, "FaceLock", "Select one or more apps to register.")
            return
        for app in selected:
            db.upsert_locked_app(
                name=app.get("name", ""),
                exec_cmd=app.get("exec", ""),
                icon=app.get("icon"),
                desktop_file=app.get("desktop_file"),
                locked=False,
                db_path=self.db_path,
            )
        self.refresh()

    def lock_selected(self) -> None:
        selected = self._selected_apps()
        if not selected:
            QMessageBox.information(self, "FaceLock", "Select one or more apps to lock.")
            return
        for app in selected:
            db.upsert_locked_app(
                name=app.get("name", ""),
                exec_cmd=app.get("exec", ""),
                icon=app.get("icon"),
                desktop_file=app.get("desktop_file"),
                locked=True,
                db_path=self.db_path,
            )
        self.refresh()

    def unlock_selected(self) -> None:
        selected = self._selected_apps()
        if not selected:
            QMessageBox.information(self, "FaceLock", "Select one or more apps to unlock.")
            return
        for app in selected:
            db.set_locked_by_identity(
                name=app.get("name"),
                exec_cmd=app.get("exec"),
                desktop_file=app.get("desktop_file"),
                locked=False,
                db_path=self.db_path,
            )
        self.refresh()


class FaceLockWindow(QMainWindow):
    def __init__(self, scan_paths: Optional[Iterable[str]] = None, db_path: Optional[str] = None) -> None:
        super().__init__()
        self.setWindowTitle("FaceLock")
        self.resize(1040, 680)
        self.scan_paths = scan_paths
        self.db_path = db_path

        root = QWidget()
        root_layout = QVBoxLayout(root)

        header = QFrame()
        header.setObjectName("Panel")
        header_layout = QVBoxLayout(header)
        title = QLabel("FaceLock")
        title.setObjectName("Title")
        subtitle = QLabel("Search apps, register them, and lock only the ones you need.")
        subtitle.setObjectName("Subtitle")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root_layout.addWidget(header)

        self.apps_tab = ApplicationsTab(scan_paths=scan_paths, db_path=db_path)
        root_layout.addWidget(self.apps_tab)

        self.setCentralWidget(root)


def build_app(scan_paths: Optional[Iterable[str]] = None, db_path: Optional[str] = None) -> tuple[QApplication, FaceLockWindow]:
    app = QApplication.instance() or QApplication([])
    _apply_dark_theme(app)
    window = FaceLockWindow(scan_paths=scan_paths, db_path=db_path)
    return app, window
