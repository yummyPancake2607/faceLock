import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import numpy as np
from PyQt6.QtWidgets import QApplication, QMessageBox

from src.facelock.database import db
from src.facelock.gui.main_window import FaceLockWindow, ProfileManagerPanel
from src.facelock.gui.face_enrollment import FaceEnrollmentDialog


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

    assert len(window.apps_panel.cards) == 1
    assert window.apps_panel.cards[0].app["name"] == "Sample App"


def test_lock_and_unlock_selected_app(tmp_path):
    app = QApplication.instance() or QApplication([])

    desktop_dir = tmp_path / "applications"
    desktop_dir.mkdir()
    _write_desktop_file(desktop_dir / "sample.desktop")

    db_path = tmp_path / "facelock.db"
    db.init_db(str(db_path))
    window = FaceLockWindow(scan_paths=[str(desktop_dir)], db_path=str(db_path))

    window.apps_panel.cards[0].toggle_button.click()
    locked_apps = db.list_locked_apps(str(db_path))
    assert len(locked_apps) == 1
    assert locked_apps[0]["locked"] is True

    window.apps_panel.cards[0].toggle_button.click()
    locked_apps = db.list_locked_apps(str(db_path))
    assert len(locked_apps) == 1
    assert locked_apps[0]["locked"] is False


def test_face_enrollment_saves_encoding_to_database(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    class FakeCamera:
        def __init__(self, index=0):
            self.index = index
            self.is_open = False

        def open(self):
            self.is_open = True
            return True

        def read_frame(self):
            return frame.copy()

        def close(self):
            self.is_open = False

    monkeypatch.setattr("src.facelock.gui.face_enrollment.Camera", FakeCamera)
    monkeypatch.setattr("src.facelock.gui.face_enrollment.detector.find_face_locations", lambda frame, model="hog": [(10, 100, 100, 10)])
    monkeypatch.setattr("src.facelock.gui.face_enrollment.encoder.encode_face", lambda crop, model="small": np.ones(128, dtype=float))

    db_path = tmp_path / "facelock.db"
    dialog = FaceEnrollmentDialog(label="alice", db_path=str(db_path))
    dialog.start_capture()
    for _ in range(20):
        dialog._capture_step()

    saved = db.get_user_encoding("alice", str(db_path))
    assert saved is not None
    assert saved.shape == (128,)


def test_profile_manager_can_delete_profile(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    db_path = tmp_path / "facelock.db"
    db.init_db(str(db_path))
    db.save_user_encoding("alice", np.ones(128, dtype=float), str(db_path))

    panel = ProfileManagerPanel(db_path=str(db_path))
    assert panel.list.count() == 1
    panel.list.setCurrentRow(0)

    monkeypatch.setattr(
        "src.facelock.gui.main_window.QMessageBox.question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    panel.delete_selected()
    assert db.list_users(str(db_path)) == []
