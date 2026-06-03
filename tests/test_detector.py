import numpy as np

from src.facelock.auth import detector


def test_to_rgb_swaps_channels():
    frame = np.array([[[10, 20, 30]]], dtype=np.uint8)

    rgb = detector._to_rgb(frame)

    np.testing.assert_array_equal(rgb, np.array([[[30, 20, 10]]], dtype=np.uint8))


def test_find_face_locations_calls_face_recognition(monkeypatch):
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    expected = [(1, 2, 3, 4)]

    def fake_face_locations(rgb, model):
        assert model == "cnn"
        np.testing.assert_array_equal(rgb, frame[:, :, ::-1])
        return expected

    monkeypatch.setattr(detector.face_recognition, "face_locations", fake_face_locations)

    locations = detector.find_face_locations(frame, model="cnn")

    assert locations == expected


def test_crop_from_location_returns_copy():
    frame = np.arange(4 * 4 * 3, dtype=np.uint8).reshape(4, 4, 3)
    location = (1, 3, 3, 4)

    crop = detector.crop_from_location(frame, location)

    np.testing.assert_array_equal(crop, frame[1:3, 3:4])
    assert crop.flags["OWNDATA"]


def test_detect_faces_returns_locations_and_optional_crops(monkeypatch):
    frame = np.arange(5 * 5 * 3, dtype=np.uint8).reshape(5, 5, 3)
    locations = [(1, 4, 3, 2), (0, 2, 2, 0)]

    monkeypatch.setattr(detector, "find_face_locations", lambda frame, model="hog": locations)

    results = detector.detect_faces(frame, model="hog", return_crops=True)

    assert len(results) == 2
    assert results[0]["location"] == locations[0]
    np.testing.assert_array_equal(results[0]["crop"], frame[1:3, 2:4])
    assert results[1]["location"] == locations[1]


def test_detect_faces_can_skip_crops(monkeypatch):
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    locations = [(0, 1, 1, 0)]

    monkeypatch.setattr(detector, "find_face_locations", lambda frame, model="hog": locations)

    results = detector.detect_faces(frame, return_crops=False)

    assert results == [{"location": locations[0], "crop": None}]


def test_draw_face_boxes_calls_cv2_rectangle(monkeypatch):
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    locations = [(1, 4, 6, 2)]
    calls = []

    def fake_rectangle(img, pt1, pt2, color, thickness):
        calls.append((pt1, pt2, color, thickness))
        return img

    monkeypatch.setattr(detector.cv2, "rectangle", fake_rectangle)

    out = detector.draw_face_boxes(frame, locations, color=(9, 8, 7), thickness=3)

    assert out is frame
    assert calls == [((2, 1), (4, 6), (9, 8, 7), 3)]