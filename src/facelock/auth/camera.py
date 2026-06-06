import typing as t
import cv2
import numpy as np


class Camera:
    """Simple camera wrapper around OpenCV's VideoCapture.

    Provides `open`, `read_frame`, and `close` helpers and supports
    use as a context manager.
    """

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self.cap: t.Optional[cv2.VideoCapture] = None
        self.error_message: str = ""

    def open(self) -> bool:
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap:
            self.error_message = f"Could not create VideoCapture for index {self.camera_index}"
            return False
        if not self.cap.isOpened():
            self.error_message = f"Camera index {self.camera_index} exists but could not be opened. Check device permissions (/dev/video{self.camera_index}) or if another app is using it."
            self.cap = None
            return False
        self.error_message = ""
        return True

    def read_frame(self) -> t.Optional[np.ndarray]:
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError("Camera is not open")

        success, frame = self.cap.read()
        if not success:
            return None
        return frame

    def close(self) -> None:
        if self.cap is not None:
            try:
                self.cap.release()
            finally:
                self.cap = None

    def __enter__(self) -> "Camera":
        if not self.open():
            raise RuntimeError(f"Could not open camera index {self.camera_index}")
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def preview_camera(camera_index: int = 0) -> None:
    """Open a window showing the camera feed until the user presses 'q'."""
    cam = Camera(camera_index)
    if not cam.open():
        raise RuntimeError(f"Could not open camera index {camera_index}")

    try:
        while True:
            frame = cam.read_frame()
            if frame is None:
                continue

            cv2.imshow("FaceLock Camera", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cam.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    preview_camera()