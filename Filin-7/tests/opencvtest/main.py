import os
import threading
os.environ["QT_QPA_PLATFORM"] = "xcb"
import cv2


import time

available_cam = [0, 2]

class CameraCapture(threading.Thread):
    def __init__(self, camera_id):
        super(CameraCapture, self).__init__()
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(camera_id)
        self.running = True
        print(self.cap)
        
        
    def run(self):
        while self.running:
            ret, frame = self.cap.read()
            print(f"cam{self.camera_id}, {frame.shape}, {ret}")
            
            if ret:
#                 cv2.imshow(f"Camera {self.camera_id}", frame)
                if cv2.waitKey(1)&0xFF == ord('q'):
                    self.running =  False
            else:
                print(f"error #{self.camera_id}")
                break
        
    def stop(self):
        self.running = False
        self.cap.release
        cv2.destroyAllWindows()
        
        
camera1 = CameraCapture(0)
camera2 = CameraCapture(2)

camera1.start()
camera2.start()

# camera1.join()
camera2.join()






# for i in range(0, 10):
#     try:
#         cap = cv2.VideoCapture(i)
#     except:
#         print(f"Camera {i} is not found!")
#     
#     if cap.isOpened():
#         available_cam.append(i)
#         cap.release()
#         
#         
# print(available_cam)

        
# 
# cap = cv2.VideoCapture(available_cam[0])
# cap1 = cv2.VideoCapture(available_cam[1])
# 
# print(cap.get(cv2.CAP_PROP_FRAME_WIDTH),cap1.get(cv2.CAP_PROP_FRAME_WIDTH))
# 
# #while True:
# ret, frame = cap.read()
# ret1, frame1 = cap1.read()
# #
# print(frame.shape, frame1.shape)
#     
# #     cv2.imshow(f"Cam 0", frame)
# #     cv2.imshow(f"Cam 2", frame1)
#     
# #     if cv2.waitKey(1)&0xFF == ord('q'):
# #         break
#     
# cap.release()
# cap1.release()
# cv2.destroyAllWindows()
# time.sleep(1)
