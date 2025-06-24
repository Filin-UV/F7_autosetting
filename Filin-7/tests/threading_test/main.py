from threading import Thread, Lock
import cv2
from time import sleep

cam1 = cv2.VideoCapture(0)
cam2 = cv2.VideoCapture(2)

def camera_capture(cam, lock: Lock):
    lock.acquire()
    ret, frame = cam.read()
    
    sleep(0.1)
    
    print(f"Cam{cam}: {frame.shape}, {ret};")
    lock.release()
    
lock = Lock()

thr1 = Thread(target=camera_capture, args=(cam1, lock,))
thr2 = Thread(target=camera_capture, args=(cam2, lock,))

thr1.start()
thr2.start()

thr1.join()
thr2.join()