import typing as t
import numpy as np
import face_recognition

def _to_rgb(frame: np.ndarray) -> np.ndarray:
    return frame[:, :, ::-1]

def encode_face(crop: np.ndarray, model: str = "small") -> t.Optional[np.ndarray]:
    """
    Return a 128-d face encoding for the provided BGR crop, or None if no encoding found.
    `model` can be "small" (faster) or "large" (more accurate).
    """
    rgb = _to_rgb(crop)
    encodings = face_recognition.face_encodings(rgb, model=model)
    return np.array(encodings[0]) if encodings else None

def encode_from_locations(frame: np.ndarray, locations: t.List[t.Tuple[int, int, int, int]], model: str = "small") -> t.List[t.Optional[np.ndarray]]:
    """
    Given a BGR `frame` and face `locations` (top,right,bottom,left), return a list of encodings
    aligned with the locations list (None for faces that couldn't be encoded).
    """
    encs: t.List[t.Optional[np.ndarray]] = []
    for (top, right, bottom, left) in locations:
        crop = frame[top:bottom, left:right].copy()
        encs.append(encode_face(crop, model=model))
    return encs

def compare_encodings(a: np.ndarray, b: np.ndarray, tolerance: float = 0.6) -> bool:
    """
    Return True if `a` and `b` represent the same person under the given `tolerance`.
    """
    if a is None or b is None:
        return False
    return face_recognition.compare_faces([a], b, tolerance=tolerance)[0]

def encoding_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two encodings (smaller -> more similar)."""
    if a is None or b is None:
        return float("inf")
    return float(np.linalg.norm(a - b))

if __name__ == "__main__":
    # quick sanity: load an image file path1/path2 and compare encodings
    import cv2
    img1 = cv2.imread("face1.jpg")
    img2 = cv2.imread("face2.jpg")
    if img1 is None or img2 is None:
        raise SystemExit("Place face1.jpg and face2.jpg in cwd for quick test.")
    enc1 = encode_face(img1)
    enc2 = encode_face(img2)
    print("Distance:", encoding_distance(enc1, enc2))
    print("Match:", compare_encodings(enc1, enc2))