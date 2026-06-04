"""Launch authentication helpers for locked app execution."""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.facelock.auth.camera import Camera
from src.facelock.auth import detector, encoder
from src.facelock.auth.system_auth import require_system_password
from src.facelock.database import db


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    bytes_per_line = channels * width
    image = QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)


def _best_face_match(frame: np.ndarray, known_encodings: list[tuple[str, np.ndarray]], tolerance: float = 0.5) -> bool:
    locations = detector.find_face_locations(frame, model="hog")
    if not locations or not known_encodings:
        return False

    encodings = encoder.encode_from_locations(frame, locations, model="small")
    for encoding in encodings:
        if encoding is None:
            continue
        for _, known_encoding in known_encodings:
            if encoder.encoding_distance(encoding, known_encoding) <= tolerance:
                return True
    return False


class FaceUnlockDialog(QDialog):
    def __init__(self, app_name: str, db_path: Optional[str] = None, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Face authentication")
        self.resize(760, 540)
        self.setModal(True)
        self.app_name = app_name
        self.db_path = db_path
        self.camera = Camera(0)
        self.timer = QTimer(self)
        self.timer.setInterval(60)
        self.timer.timeout.connect(self._capture_step)
        self.timeout_timer = QTimer(self)
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.setInterval(8000)
        self.timeout_timer.timeout.connect(self._face_timeout)
        self.known_encodings: list[tuple[str, np.ndarray]] = []
        self._active = False
        self._timed_out = False

        for row in db.list_users(self.db_path):
            encoding = db.get_user_encoding(row["label"], self.db_path)
            if encoding is not None:
                self.known_encodings.append((row["label"], encoding))

        root = QVBoxLayout(self)
        root.setSpacing(12)

        title = QLabel(f"Face check for {self.app_name}")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        root.addWidget(title)

        self.preview = QLabel("Camera preview will appear here")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(320)
        self.preview.setStyleSheet(
            "background: #0e1728; border: 1px dashed #263d63; border-radius: 12px; color: #90a7d3;"
        )
        root.addWidget(self.preview)

        self.status = QLabel("Look at the camera to unlock the app.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("background: transparent; color: #90a7d3;")
        root.addWidget(self.status)

        actions = QHBoxLayout()
        self.password_button = QPushButton("Use Password")
        self.password_button.setProperty("secondary", True)
        self.password_button.clicked.connect(self.reject)
        actions.addWidget(self.password_button)

        actions.addStretch(1)

        cancel = QPushButton("Cancel")
        cancel.setProperty("secondary", True)
        cancel.clicked.connect(self.reject)
        actions.addWidget(cancel)

        root.addLayout(actions)

        QTimer.singleShot(0, self.start_capture)

    def start_capture(self) -> None:
        if self._active:
            return
        if not self.known_encodings:
            self.status.setText("No face profiles are registered yet.")
            self.reject()
            return
        if not self.camera.open():
            self.status.setText("Could not open the camera.")
            self.reject()
            return
        self._active = True
        self.timer.start()
        self.timeout_timer.start()

    def _finish(self, accepted: bool) -> None:
        if not self._active:
            return
        self._active = False
        self.timer.stop()
        self.camera.close()
        if accepted:
            self.accept()
        else:
            self.reject()

    def _close_for_password(self) -> None:
        self.timer.stop()
        self.timeout_timer.stop()
        self.camera.close()
        self._active = False

    def _close_with_rejection(self) -> None:
        self._close_for_password()
        super().reject()

    def _finish_timeout(self) -> None:
        self._close_with_rejection()

    def _face_timeout(self) -> None:
        if not self._active:
            return
        self._timed_out = True
        self.status.setText("Face not identified. Enter password.")
        self._finish_timeout()

    def _capture_step(self) -> None:
        if not self._active:
            return

        frame = self.camera.read_frame()
        if frame is None:
            return

        display = frame.copy()
        faces = detector.find_face_locations(frame, model="hog")
        if faces:
            detector.draw_face_boxes(display, faces)
            if _best_face_match(frame, self.known_encodings):
                self.status.setText("Face authenticated.")
                self.preview.setPixmap(
                    _frame_to_pixmap(display).scaled(
                        self.preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self._finish(True)
                return
            self.status.setText("Face not authenticated. Try again or use password.")

        if self._timed_out and not faces:
            self.status.setText("Face not identified. Enter password.")

        pixmap = _frame_to_pixmap(display).scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(pixmap)

    def reject(self) -> None:
        self._close_with_rejection()

    def closeEvent(self, event) -> None:
        self._close_for_password()
        super().closeEvent(event)


def authenticate_locked_launch(
    app_name: str,
    parent: Optional[QWidget] = None,
    db_path: Optional[str] = None,
) -> tuple[bool, str]:
    """Authenticate a locked app launch with face first, then password fallback."""
    dialog = FaceUnlockDialog(app_name=app_name, db_path=db_path, parent=parent)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return True, "face"

    timed_out = getattr(dialog, "_timed_out", False)
    timeout_message = (
        f"Face not identified for {app_name}. Enter your password to continue."
        if timed_out
        else f"Face not authenticated for {app_name}. Enter your password to continue."
    )
    if require_system_password(
        parent,
        message=timeout_message,
    ):
        return True, "password"

    QMessageBox.warning(parent, "FaceLock", f"Access denied for {app_name}.")
    return False, "denied"