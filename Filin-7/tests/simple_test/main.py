import os
os.environ["QT_QPA_PLATFORM"] = "xcb"
import cv2
from time import sleep
import RPi.GPIO as GPIO

pwm_pin = 12
GPIO.setwarnings(False)         #disable warnings
GPIO.setmode(GPIO.BCM)        #set pin numbering system
GPIO.setup(pwm_pin,GPIO.OUT)

pi_pwm = GPIO.PWM(pwm_pin,1500) #create PWM instance with frequency
pi_pwm.start(0)

cam1 = cv2.VideoCapture(2, cv2.CAP_V4L2)
cam2 = cv2.VideoCapture(0, cv2.CAP_V4L2)
# cam1.open(4)
# cam2.open(7)
print(cam1.set(cv2.CAP_PROP_FRAME_WIDTH, 640))
print(cam1.set(cv2.CAP_PROP_FRAME_HEIGHT, 480))
print(cam2.set(cv2.CAP_PROP_FRAME_WIDTH, 176))
print(cam2.set(cv2.CAP_PROP_FRAME_HEIGHT, 144))
# print(cam2.set(cv2.CAP_PROP_SATURATION, 0))

duty = 90
while True:
    pi_pwm.ChangeDutyCycle(duty) #provide duty cycle in the range 0-100
        
    print(duty)
    if duty < 99:
        duty = duty + 0.1
    else:
        duty = 90
    ret, frame = cam1.read()
    ret1, frame1 = cam2.read()
    print(f"Cam{cam1}: {frame.shape}, {ret}, {cam1.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cam1.get(cv2.CAP_PROP_FRAME_HEIGHT)};")
        #print(f"Cam {cam} is {cam.isOpened()}")
    frame1 = cv2.resize(frame1, (640, 480), interpolation = cv2.INTER_AREA)
    frame1 = cv2.threshold(frame1, 115, 255, cv2.THRESH_BINARY)
    frame2 = cv2.addWeighted(frame, 1.0, frame1[1], 1.0, 0) 
    cv2.imshow("cam2", frame2)
#     sleep(1.0)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        cam1.release()
        cam2.release()
        break
cv2.destroyWindow("cam2")




# def camera_capture(cam, name):
#     while True:
#         ret, frame = cam.read()
# #         print(f"Cam{cam}: {frame.shape}, {ret}, {cam.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cam.get(cv2.CAP_PROP_FRAME_HEIGHT)};")
#         #print(f"Cam {cam} is {cam.isOpened()}")    
#         cv2.imshow(name, frame)
#         sleep(1.0)
#         if cv2.waitKey(0) & 0xFF == ord('q'):
#             cam.release()
#             break
# 
#     cv2.destroyWindow(name)
#         
# 
# 
# 
# thr1 = Process(target=camera_capture, args=(cam1,"cam1",), daemon=True)
# # thr2 = Process(target=camera_capture, args=(cam2,"cam2",), daemon=True)
# 
# thr1.start()
# # thr2.start()
# 
# thr1.join()
# # thr2.join()