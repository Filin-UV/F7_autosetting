import os
os.environ["OPENCV_LOG_LEVEL"]="SILENT"
import cv2

def get_camera_info():
    active_cam = []
    index = 0
    while index < 10:
        try:
            camera = cv2.VideoCapture(index)
        except:
            print(f"Camera {index} is not available")
            break
        if camera.isOpened():
            active_cam.append(index)
            print(f"Camera {index} active")
            camera.release()
        index += 1
    return active_cam

if __name__ == "__main__":
    print(get_camera_info())
    print("Thats all!")