import time
import typing as t

import numpy as np

from . import detector, encoder
from .storage import FileStore


class FaceService:
    def __init__(self, store: t.Optional[FileStore] = None, encode_model: str = "small"):
        self.store = store or FileStore()
        self.encode_model = encode_model

    def register_from_crop(self, crop: np.ndarray, label: str) -> t.Optional[str]:
        enc = encoder.encode_face(crop, model=self.encode_model)
        if enc is None:
            return None
        return self.store.save(enc, label)

    def register_from_frame(
        self,
        frame: np.ndarray,
        location: t.Tuple[int, int, int, int],
        label: str,
    ) -> t.Optional[str]:
        top, right, bottom, left = location
        crop = frame[top:bottom, left:right].copy()
        return self.register_from_crop(crop, label)

    def recognize(self, frame: np.ndarray, model: str = "hog", tolerance: float = 0.6) -> t.List[dict]:
        """
        Detect faces in `frame`, encode them, and compare against stored identities.
        Returns list of results:
        {
            "location": (top, right, bottom, left),
            "encoding": np.ndarray | None,
            "match_id": str | None,
            "label": str | None,
            "distance": float
        }
        """
        locations = detector.find_face_locations(frame, model=model)
        encodings = encoder.encode_from_locations(frame, locations, model=self.encode_model)
        results: t.List[dict] = []

        known = [
            (key, record["encoding"], record["label"])
            for key, record in self.store.list().items()
            if record.get("encoding") is not None
        ]

        for location, encoding in zip(locations, encodings):
            best_id = None
            best_label = None
            best_distance = float("inf")

            if encoding is not None:
                for key, known_encoding, known_label in known:
                    distance = encoder.encoding_distance(encoding, known_encoding)
                    if distance < best_distance:
                        best_distance = distance
                        best_id = key
                        best_label = known_label

                if best_distance > tolerance:
                    best_id = None
                    best_label = None

            results.append(
                {
                    "location": location,
                    "encoding": encoding,
                    "match_id": best_id,
                    "label": best_label,
                    "distance": best_distance,
                }
            )

        return results

    def list_known(self) -> t.Dict[str, dict]:
        return self.store.list()

    def remove_known(self, key: str) -> bool:
        return self.store.remove(key)


if __name__ == "__main__":
    import cv2

    svc = FaceService()
    a = cv2.imread("known1.jpg")
    b = cv2.imread("known2.jpg")
    test = cv2.imread("test.jpg")

    if a is None or b is None or test is None:
        raise SystemExit("Place known1.jpg, known2.jpg, and test.jpg in the cwd for the quick demo.")

    la = detector.find_face_locations(a)
    lb = detector.find_face_locations(b)

    if la:
        svc.register_from_frame(a, la[0], label="personA")
    if lb:
        svc.register_from_frame(b, lb[0], label="personB")

    res = svc.recognize(test)
    for item in res:
        print(item["location"], "->", item["label"], "distance:", item["distance"])