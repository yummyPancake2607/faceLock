import cv2

class Camera:
    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.cap = None

    def open(self) ->bool:
        self.cap = cv2.VideoCapture(self.camera_index)
        return self.cap.isOpened()
    
    def read_frame(self):
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError("camera is not open")
        
        success, frame = self.cap.read()
        if not success:
            return None
        
        return frame
    
    def close(self)->None:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

def preview_camera(camera_index: int = 0) -> None:
    camera = Camera(camera_index)
    if not camera.open():
        raise RuntimeError("could not Open Camera")
    
    try:
        while True:
            frame = camera.read_frame()
            if frame is None:
                continue

            cv2.imshow("FaceLock Camera", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        camera.close()
        cv2.destoryAllWindows()

if __name__ == "__main__":
    preview_camera()