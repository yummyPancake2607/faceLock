"""Face enrollment dialog that captures camera frames and saves encodings."""
from __future__ import annotations

import statistics
from typing import Optional

import cv2
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from src.facelock.auth.camera import Camera
from src.facelock.auth import detector, encoder
from src.facelock.database import db


def _frame_to_pixmap(frame: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    height, width, channels = rgb.shape
    bytes_per_line = channels * width
    image = QImage(rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(image)


class FaceEnrollmentDialog(QDialog):
    def __init__(self, label: str, db_path: Optional[str] = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Register Face")
        self.resize(760, 540)
        self.label = label
        self.db_path = db_path
        self.samples_target = 20
        self.encodings: list[np.ndarray] = []
        self._finished = False
        self.camera = Camera(0)
        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._capture_step)

        root = QVBoxLayout(self)
        root.setSpacing(12)

        panel = QFrame()
        panel_layout = QVBoxLayout(panel)

        self.title = QLabel(f"Register face for: {label}")
        self.title.setStyleSheet("font-size: 18px; font-weight: 700;")
        panel_layout.addWidget(self.title)

        self.preview = QLabel("Camera preview will appear here")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumHeight(320)
        self.preview.setStyleSheet(
            "background: #0e1728; border: 1px dashed #263d63; border-radius: 12px; color: #90a7d3;"
        )
        panel_layout.addWidget(self.preview)

        self.status = QLabel("Press Start to open the camera and begin sampling your face.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("background: transparent; color: #90a7d3;")
        panel_layout.addWidget(self.status)

        root.addWidget(panel)

        buttons = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_capture)
        buttons.addWidget(self.start_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setProperty("secondary", True)
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.cancel_button)

        buttons.addStretch(1)
        root.addLayout(buttons)

    def start_capture(self) -> None:
        if not self.camera.open():
            QMessageBox.critical(self, "OwlLock", "Could not open the camera.")
            return
        self.encodings = []
        self.start_button.setEnabled(False)
        self.status.setText(f"Capturing face samples for {self.label}... {len(self.encodings)}/{self.samples_target}")
        self.timer.start()

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self.timer.stop()
        self.camera.close()
        self.start_button.setEnabled(True)

        if not self.encodings:
            self.status.setText("No usable face samples were captured.")
            return

        representation = np.mean(np.vstack(self.encodings), axis=0)
        db.save_user_encoding(self.label, representation, self.db_path)
        self.status.setText(f"Saved face profile '{self.label}' to the database.")
        self.accept()

    def _capture_step(self) -> None:
        if self._finished:
            return
        frame = self.camera.read_frame()
        if frame is None:
            return

        faces = detector.find_face_locations(frame, model="hog")
        display = frame.copy()
        if faces:
            detector.draw_face_boxes(display, faces)
            top, right, bottom, left = faces[0]
            crop = frame[top:bottom, left:right].copy()
            face_encoding = encoder.encode_face(crop, model="small")
            if face_encoding is not None:
                self.encodings.append(face_encoding)
                self.status.setText(
                    f"Capturing face samples for {self.label}... {len(self.encodings)}/{self.samples_target}"
                )

        pixmap = _frame_to_pixmap(display).scaled(
            self.preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview.setPixmap(pixmap)

        if len(self.encodings) >= self.samples_target:
            self._finish()

    def reject(self) -> None:
        self.timer.stop()
        self.camera.close()
        super().reject()
