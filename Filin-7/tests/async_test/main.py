import asyncio
import cv2
from time import sleep

cam1 = cv2.VideoCapture(0)
cam2 = cv2.VideoCapture(3)

async def camera_capture(cam):
    ret, frame = cam.read()
    print(f"Cam{cam}: {frame.shape}, {ret};")
    
async def starter():
    await asyncio.gather(camera_capture(cam1), camera_capture(cam2))
    
    
asyncio.run(starter())