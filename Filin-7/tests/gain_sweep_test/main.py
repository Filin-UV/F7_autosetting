import numpy as np
import timeit
from itertools import cycle
import os
from kivy.clock import Clock
os.environ["OPENCV_LOG_LEVEL"]="SILENT"
os.environ["QT_QPA_PLATFORM"] = "xcb"
import cv2
import colorsys

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

##video_capture = Clock.schedule_interval(self.update_video, 1.0/30.0)
cam_list = get_camera_info()

video_input1 = cv2.VideoCapture(cam_list[0])
video_input2 = cv2.VideoCapture(cam_list[1])
print(video_input1.set(cv2.CAP_PROP_FRAME_WIDTH, 640))
print(video_input1.set(cv2.CAP_PROP_FRAME_HEIGHT, 480))
print(video_input2.set(cv2.CAP_PROP_FRAME_WIDTH, 176))
print(video_input2.set(cv2.CAP_PROP_FRAME_HEIGHT, 144))
name = '750'
areas = []
frame2_old = np.zeros([480, 640, 3], dtype = np.uint8)
ret1, frame1 = video_input1.read()
ret2, frame2 = video_input2.read()
frame2 = cv2.resize(frame2, (640, 480), interpolation = cv2.INTER_AREA)
# for gain in range(255, 0,-1):
#     frame2_loc = frame2
#     print('gain = ', gain)
#     gr = cv2.cvtColor(frame2_loc, cv2.COLOR_BGR2GRAY)
#     frame2_thr = cv2.threshold(gr, 255 - gain, 255, cv2.THRESH_BINARY)[1]
#     mask = cv2.merge([frame2_thr, frame2_thr,frame2_thr])
#     contours, _ = cv2.findContours(frame2_thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
#     if len(contours) > 0:
#         area_loc = []
#         for contour in contours:
#             area_loc.append(cv2.contourArea(contour))
#         areas.append(max(area_loc))
#     else:
#         areas.append(0)
#     r, g, b = colorsys.hsv_to_rgb(gain/255, 1.0, 1.0)
#     print(r, g, b, gain)
#     frame2_thr = cv2.merge([(b*frame2_thr).astype(np.uint8), (g*frame2_thr).astype(np.uint8), (r*frame2_thr).astype(np.uint8)])             
#     #frame2_old = cv2.add(cv2.bitwise_and(frame2_old, cv2.bitwise_not(mask)), frame2_thr)
#     frame2_o = frame2_thr
#     if True:
#         frame2_o = cv2.putText(frame2_o, "gain = {}".format(gain), (50,50), cv2.FONT_HERSHEY_SIMPLEX,1, (b*255,g*255,r*255), 2, cv2.LINE_AA)
#         cv2.imwrite('{}/{}-{}-sub.jpg'.format(name, name, gain), frame2_thr)                        


frame3 = cv2.addWeighted(frame1, 0.8, frame2, 1.0, 0)
        
print(areas)
video_input1.release()
video_input2.release()

cv2.imwrite('{}/{}-uv.jpg'.format(name, name), frame2)
cv2.imwrite('{}/{}-mix.jpg'.format(name, name), frame3)
# with open('{}/{}.txt'.format(name, name), 'w') as output:
#     output.write(str(areas))

