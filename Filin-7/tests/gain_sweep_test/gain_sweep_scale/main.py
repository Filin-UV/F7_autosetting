import numpy as np
import timeit
from itertools import cycle
import os
from kivy.clock import Clock
os.environ["OPENCV_LOG_LEVEL"]="SILENT"
os.environ["QT_QPA_PLATFORM"] = "xcb"
import cv2
import colorsys

scale = np.ones((480,640,3), dtype=np.uint8)*255
for gain in range(255, 0,-1):
    r, g, b = colorsys.hsv_to_rgb(gain/255, 1.0, 1.0)
    if gain % 25 == 0:
        scale = cv2.line(scale, (0, gain), (60, gain), (255*b, 255*g, 255*r), 1)
    else:
        scale = cv2.line(scale, (20, gain), (60, gain), (255*b, 255*g, 255*r), 1)
    #print(r,g,b,gain)

cv2.imwrite('scale.jpg', scale)

