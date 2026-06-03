import numpy as np

from src.facelock.auth import encoder


def test_encode_face_and_distance(monkeypatch):
    # fake face_recognition.face_encodings to return a known vector
    def fake_face_encodings(rgb, model='small'):
        return [[0.1] * 128]

    monkeypatch.setattr(encoder.face_recognition, 'face_encodings', fake_face_encodings)

    crop = np.zeros((10, 10, 3), dtype=np.uint8)
    enc = encoder.encode_face(crop)
    assert enc is not None
    assert len(enc) == 128

    # distance to identical vector should be zero
    assert abs(encoder.encoding_distance(enc, enc)) < 1e-6


def test_encode_from_locations_and_compare(monkeypatch):
    # Return the same encoding for any crop
    def fake_face_encodings(rgb, model='small'):
        return [[0.2] * 128]

    monkeypatch.setattr(encoder.face_recognition, 'face_encodings', fake_face_encodings)
    monkeypatch.setattr(encoder.face_recognition, 'compare_faces', lambda known, probe, tolerance=0.6: [True])

    frame = np.zeros((5, 5, 3), dtype=np.uint8)
    locations = [(0, 5, 5, 0)]
    encs = encoder.encode_from_locations(frame, locations)
    assert len(encs) == 1
    assert encs[0] is not None

    a = encs[0]
    b = encs[0].copy()
    assert encoder.compare_encodings(a, b)
