import numpy as np

from src.facelock.auth.camera import Camera


def test_open_read_and_close(monkeypatch):
    calls = {}

    class FakeCap:
        def __init__(self):
            self.opened = True
            self.released = False

        def isOpened(self):
            return self.opened

        def read(self):
            # return a simple 2x2 BGR frame
            return True, np.zeros((2, 2, 3), dtype=np.uint8)

        def release(self):
            self.released = True
            calls['released'] = True

    monkeypatch.setattr('cv2.VideoCapture', lambda idx: FakeCap())

    cam = Camera(0)
    assert cam.open() is True
    frame = cam.read_frame()
    assert frame.shape == (2, 2, 3)
    cam.close()
    assert calls.get('released', False) is True


def test_context_manager_opens_and_closes(monkeypatch):
    class FakeCap2:
        def __init__(self):
            self.opened = True
            self.released = False

        def isOpened(self):
            return True

        def read(self):
            return True, np.ones((1, 1, 3), dtype=np.uint8)

        def release(self):
            self.released = True

    monkeypatch.setattr('cv2.VideoCapture', lambda idx: FakeCap2())

    with Camera(0) as cam:
        f = cam.read_frame()
        assert f.shape == (1, 1, 3)


def test_read_frame_without_open_raises():
    cam = Camera(0)
    try:
        cam.read_frame()
        raise AssertionError('read_frame should raise when camera is not open')
    except RuntimeError:
        pass
