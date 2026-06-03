import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

from PyQt6.QtWidgets import QApplication

from src.facelock.database import db
from src.facelock.gui.main_window import FaceLockWindow


def _write_desktop_file(path: Path) -> None:
    path.write_text(
        """
[Desktop Entry]
Type=Application
Name=Sample App
Exec=sample-app %U
Icon=sample-icon
Categories=Utility;
""".strip(),
        encoding="utf-8",
    )


def test_window_loads_scanned_apps(tmp_path):
    app = QApplication.instance() or QApplication([])

    desktop_dir = tmp_path / "applications"
    desktop_dir.mkdir()
    _write_desktop_file(desktop_dir / "sample.desktop")

    db_path = tmp_path / "facelock.db"
    db.init_db(str(db_path))
    window = FaceLockWindow(scan_paths=[str(desktop_dir)], db_path=str(db_path))

    assert window.apps_tab.table.rowCount() == 1
    assert window.apps_tab.table.item(0, 0).text() == "Sample App"


def test_lock_and_unlock_selected_app(tmp_path):
    app = QApplication.instance() or QApplication([])

    desktop_dir = tmp_path / "applications"
    desktop_dir.mkdir()
    _write_desktop_file(desktop_dir / "sample.desktop")

    db_path = tmp_path / "facelock.db"
    db.init_db(str(db_path))
    window = FaceLockWindow(scan_paths=[str(desktop_dir)], db_path=str(db_path))

    window.apps_tab.table.selectRow(0)
    window.apps_tab.lock_selected()
    locked_apps = db.list_locked_apps(str(db_path))
    assert len(locked_apps) == 1
    assert locked_apps[0]["locked"] is True

    window.apps_tab.unlock_selected()
    locked_apps = db.list_locked_apps(str(db_path))
    assert len(locked_apps) == 1
    assert locked_apps[0]["locked"] is False


def test_register_selected_app_persists_to_db(tmp_path):
    app = QApplication.instance() or QApplication([])

    desktop_dir = tmp_path / "applications"
    desktop_dir.mkdir()
    _write_desktop_file(desktop_dir / "sample.desktop")

    db_path = tmp_path / "facelock.db"
    db.init_db(str(db_path))
    window = FaceLockWindow(scan_paths=[str(desktop_dir)], db_path=str(db_path))

    window.apps_tab.table.selectRow(0)
    window.apps_tab.register_selected()

    locked_apps = db.list_locked_apps(str(db_path))
    assert len(locked_apps) == 1
    assert locked_apps[0]["name"] == "Sample App"
    assert locked_apps[0]["locked"] is False
