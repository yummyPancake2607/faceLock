import typing as t
import uuid
import time
import numpy as np
from . import detector, encoder

class InMemoryStore:
    def __init__(self):
        self._data: t.Dict[str, dict] = {}

    def save(self, encoding: np.ndarray, label: str) -> str:
        key = str(uuid.uuid4())
        self._data[key] = {"encoding": encoding, "label": label, "created_at": time.time()}
        return key

    def list(self) -> t.Dict[str, dict]:
        return dict(self._data)

    def get(self, key: str) -> t.Optional[dict]:
        return self._data.get(key)

    def remove(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

class FaceService:
    def __init__(self, store: t.Optional[InMemoryStore] = None, encode_model: str = "small"):
        self.store = store or InMemoryStore()
        self.encode_model = encode_model

    def register_from_crop(self, crop: np.ndarray, label: str) -> t.Optional[str]:
        enc = encoder.encode_face(crop, model=self.encode_model)
        if enc is None:
            return None
        return self.store.save(enc, label)

    def register_from_frame(self, frame: np.ndarray, location: t.Tuple[int, int, int, int], label: str) -> t.Optional[str]:
        top, right, bottom, left = location
        crop = frame[top:bottom, left:right].copy()
        return self.register_from_crop(crop, label)

    def recognize(self, frame: np.ndarray, model: str = "hog", tolerance: float = 0.6) -> t.List[dict]:
        """
        Detect faces in `frame`, encode them, and compare against stored identities.
        Returns list of results: {
            "location": (top,right,bottom,left),
            "encoding": np.ndarray | None,
            "match_id": str | None,
            "label": str | None,
            "distance": float
        }
        """
        locations = detector.find_face_locations(frame, model=model)
        encs = encoder.encode_from_locations(frame, locations, model=self.encode_model)
        results: t.List[dict] = []

        known = [(k, v["encoding"], v["label"]) for k, v in self.store.list().items()]

        for loc, enc in zip(locations, encs):
            best_id = None
            best_label = None
            best_distance = float("inf")
            if enc is not None and known:
                for kid, kenc, klabel in known:
                    d = encoder.encoding_distance(enc, kenc)
                    if d < best_distance:
                        best_distance = d
                        best_id = kid
                        best_label = klabel
                if best_distance > tolerance:
                    best_id = None
                    best_label = None
            results.append({
                "location": loc,
                "encoding": enc,
                "match_id": best_id,
                "label": best_label,
                "distance": best_distance,
            })
        return results

    def list_known(self) -> t.Dict[str, dict]:
        return self.store.list()

    def remove_known(self, key: str) -> bool:
        return self.store.remove(key)

if __name__ == "__main__":
    # Quick demo: register two images and compare a test image
    import cv2
    svc = FaceService()
    a = cv2.imread("known1.jpg")
    b = cv2.imread("known2.jpg")
    test = cv2.imread("test.jpg")
    if a is None or b is None or test is None:
        raise SystemExit("Place known1.jpg, known2.jpg and test.jpg in cwd for quick demo.")

    # naive: detect first face in each image and register
    la = detector.find_face_locations(a)
    lb = detector.find_face_locations(b)
    if la:
        svc.register_from_frame(a, la[0], label="personA")
    if lb:
        svc.register_from_frame(b, lb[0], label="personB")

    res = svc.recognize(test)
    for r in res:
        print(r["location"], "->", r["label"], "distance:", r["distance"])