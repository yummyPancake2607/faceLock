import typing as t
import cv2
import numpy as np
import face_recognition


def _to_rgb(frame: np.ndarray) -> np.ndarray:
    return frame[:, :, ::-1]


def find_face_locations(frame: np.ndarray, model: str = "hog") -> t.List[t.Tuple[int, int, int, int]]:
    """
    Return face locations as (top, right, bottom, left).
    `model` can be "hog" (fast, CPU) or "cnn" (more accurate, needs GPU + dlib/cuda).
    """
    rgb = _to_rgb(frame)
    return face_recognition.face_locations(rgb, model=model)


def crop_from_location(frame: np.ndarray, loc: t.Tuple[int, int, int, int]) -> np.ndarray:
    top, right, bottom, left = loc
    return frame[top:bottom, left:right].copy()


def detect_faces(frame: np.ndarray, model: str = "hog", return_crops: bool = True) -> t.List[t.Dict]:
    """
    Detect faces and optionally return crops.
    Returns list of dicts: {"location": (t,r,b,l), "crop": np.ndarray | None}
    """
    locations = find_face_locations(frame, model=model)
    results = []
    for loc in locations:
        crop = crop_from_location(frame, loc) if return_crops else None
        results.append({"location": loc, "crop": crop})
    return results


def draw_face_boxes(frame: np.ndarray, locations: t.List[t.Tuple[int, int, int, int]], color=(0, 255, 0), thickness: int = 2) -> np.ndarray:
    """
    Draw rectangles on the provided BGR frame in-place and return it.
    """
    for (top, right, bottom, left) in locations:
        cv2.rectangle(frame, (left, top), (right, bottom), color, thickness)
    return frame


if __name__ == "__main__":
    # quick live test: open camera and show detections
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise SystemExit("Could not open camera (index 0).")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                continue

            faces = detect_faces(frame, model="hog", return_crops=False)
            locations = [f["location"] for f in faces]
            draw_face_boxes(frame, locations)
            cv2.imshow("FaceLock Detector", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()