from kivy.config import Config
#Config.set('postproc', 'double_tap_time', '10')
from kivy import require
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.togglebutton import ToggleButton
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle
from kivy.core.window import Window
import numpy as np
import timeit
from itertools import cycle
import os
os.environ["OPENCV_LOG_LEVEL"]="SILENT"
os.environ["QT_QPA_PLATFORM"] = "linuxfb"
import cv2
import datetime
import subprocess
import re
import xml.etree.ElementTree as ET
import adafruit_dht
import board
import configparser
import time
import hashlib

sw_version = '2.2.0'

require("2.3.0")
debug = 0
video_debug = 0

if debug == 0:
    Window.show_cursor = False
    Window.size = (800, 500)
    Window.borderless = True
    Window.maximize()
else:
    Window.show_cursor = True
    Window.size = (800, 480)
    Window.borderless = False
    Window.resizeable = False
    

#Variables
menu_visibility = True
modes_visibility = False
thr_sl_visibility = False
record_video = False
Analysis = False
info_flag = False
temp_celsius = True
area_counter = 0
area = []
area_avg = 0
area_frame_max = 25
thr_sl_val = 55
click_types = cycle(["Shot", "Capture", "Expose"])
zoomstr = cycle([1, 2, 4])
DOUBLE_TAP_TIME = 0.2   # Change time in seconds
LONG_PRESSED_TIME = 0.3  # Change time in seconds
debounce = 0
preview_data = []
frame1 = []
frame2 = []
save_all_data = True
gallery_image_path = ''

########################GLOBAL SETTINGS################
cnfgprs = configparser.ConfigParser()
localeprs = configparser.ConfigParser()
devmodeprs = configparser.ConfigParser()
hash_etalon = 'ee79976c9380d5e337fc1c095ece8c8f22f91f306ceeb161fa51fecede2c4ba1'
language = 0
spot_color = [0, 0, 0]
capt_m = 0
acc_period = 0
temp_u = 0
save_m = 0

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
            print(f"Camera 4cc - {camera.get(cv2.CAP_PROP_FOURCC)}")
            print(f"Camera bitrate - {camera.get(cv2.CAP_PROP_BITRATE)}")
            print(f"Camera backend - {camera.get(cv2.CAP_PROP_BACKEND)}")
            camera.release()
        index += 1
    return active_cam


# Declare both screens
class InitScreen(Screen):
    def on_enter(self):
        self.progress_value = 0
        self.ver_label.text = 'ver.{}'.format(sw_version)
        if debug == 1:
            self.progress_inc = 100
        else:
            self.progress_inc = 1

        self.progress_event = Clock.schedule_interval(self.update_progress, 0.05)
    
    def update_progress(self, dt):
        self.progress_value += self.progress_inc
        self.lp.value = self.progress_value
        if self.progress_value >= 100:
            self.progress_event.cancel()
            self.manager.current = "main"

class MainScreen(Screen):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_touch_move=self.detect_swipe)
        #self.shot_button.bind(on_touch_move=self.detect_shot_swipe)
        #self.shot_button.bind(on_touch_up=self.shot_clicked)
        self.debounce_event = Clock.schedule_interval(self.update_debouce, 1)
        self.video_capture = Clock.schedule_interval(self.update_video, 1.0/30.0)
        
        cam_list = get_camera_info()
        if video_debug == 0:
            self.video_input1 = cv2.VideoCapture(cam_list[0])
            self.video_input2 = cv2.VideoCapture(cam_list[1])
            print(self.video_input1.set(cv2.CAP_PROP_FRAME_WIDTH, 640))
            print(self.video_input1.set(cv2.CAP_PROP_FRAME_HEIGHT, 480))
            print(self.video_input2.set(cv2.CAP_PROP_FRAME_WIDTH, 176))
            print(self.video_input2.set(cv2.CAP_PROP_FRAME_HEIGHT, 144))

        self.current_mode = 0
        self.current_thr = int(255.0 * 0.95)
        result = subprocess.run(['pgrep', 'libgpiod_pulse'], capture_output = True, text = True)
        lines = result.stdout.split('\n')
        for el in lines:
            result = subprocess.run(['kill', el], capture_output = True, text = True)
        self.dht_device = adafruit_dht.DHT22(board.D18)
        
        self.mode_button.text = loc_dict['mode_t']
        self.thr_button.text = loc_dict['threshold_t']
        self.ai_button.text = loc_dict['analysis_t']
        self.shot_button.text = loc_dict['shot_t']
        self.settings_button.text = loc_dict['settings_t']
        self.mxmd.text = loc_dict['mix_t']
        self.uvmd.text = loc_dict['uv_t']
        self.vsmd.text = loc_dict['vis_t']
    def on_enter(self):
        if capt_m == 0:
            self.shot_button.text = loc_dict['one_shot_t']
        elif capt_m == 1:
            self.shot_button.text = loc_dict['accum_shot_t']
        elif capt_m == 2:
            self.shot_button.text = loc_dict['video_t']
    def update_video(self, dt):
        global area, area_counter, area_avg
        global frame1, frame2
        if video_debug == 0:
            ret1, frame1 = self.video_input1.read()
            ret2, frame2 = self.video_input2.read()
        else:
            frame1 = cv2.imread("res/vis_test.jpg")
            frame2 = cv2.imread("res/uv_test.jpg")
        print(frame2.max())
            
        
        if self.current_mode ==  2:
            buf1 = cv2.flip(frame1, 0)
            buf = buf1.tobytes()
            texture = Texture.create(size=(frame1.shape[1], frame1.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.canva.texture = texture
        elif self.current_mode == 1:
            frame2 = cv2.resize(frame2, (640, 480), interpolation = cv2.INTER_AREA)
            buf1 = cv2.flip(frame2, 0)
            buf = buf1.tobytes()
            texture = Texture.create(size=(frame1.shape[1], frame1.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.canva.texture = texture
        elif self.current_mode == 0:
            frame2 = cv2.resize(frame2, (640, 480), interpolation = cv2.INTER_AREA)
            gr = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
            frame2_thr = cv2.threshold(gr, 255 - thr_sl_val, 255, cv2.THRESH_BINARY)[1]
            if Analysis:
#                 self.histo = self.count_histo(gr)
#                 histogram = np.zeros((129,204,3), np.uint8)
#                 cv2.line(histogram, (30,110), (180, 110), (255,255, 255), 1)
#                 cv2.line(histogram, (30,110), (30, 10), (255,255, 255), 1)
#                 cv2.line(histogram, (285 - int(thr_sl_val),110), (285 - int(thr_sl_val), 10), (255,255, 255), 1)
#                 for i in range(10):
#                     cv2.line(histogram, (28,110 - (i+1)*10), (32, 110 - (i+1)*10), (255,255, 255), 1)
#                 for i in range(25):
#                     cv2.line(histogram, (30 + (i+1)*6,108), (30 + (i+1)*6, 112), (255,255, 255), 1)
#                 for i in range(len(self.histo)):
#                     print(i, self.histo[i])
#                     #cv2.line(histogram, (38 + i*16,110), (38 + i*16, 110 - self.histo[i]), (255 - i*10,i*10, 255), 16, lineType = cv2.LINE_AA)
#                     cv2.rectangle(histogram, (30 + i*3,  110 - self.histo[i]*10), (30 + (i+1)*3, 110), color = (255 - i*5,i*5, 255), thickness = -1)
#                 buf1 = cv2.flip(histogram, 0)
#                 buf = buf1.tobytes()
#                 self.texture = Texture.create(size=(histogram.shape[1], histogram.shape[0]), colorfmt='bgr')
#                 self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
#                 self.histo_c.texture = self.texture
# #                 self.h1.points = [self.pos[0] + 40, self.pos[1] + 20, self.pos[0] + 40, self.pos[1] + 20 + self.hysto[0]]
# #                 self.h2.points = [self.pos[0] + 40, self.pos[1] + 20, self.pos[0] + 40, self.pos[1] + 20 + self.hysto[1]]                
# #                 
#                 self.histo_l.opacity = 100
                ai_frame = frame2_thr
                contours, _ = cv2.findContours(ai_frame, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if area_counter > area_frame_max:
                    area = [0]
                    area_counter = 0
                else:
                    area_counter = area_counter + 1
                    
                if len(contours) > 0:
                    area_loc = []
                    for contour in contours:
                        area_loc.append(cv2.contourArea(contour))
                    area.append(max(area_loc))
                else:
                    area = [0]
                #frame3 = cv2.addWeighted(frame1, 1.0, ai_frame, 1.0, 0)
                if area_counter == area_frame_max:
                    area_avg = round(sum(area)/len(area),1)
                ai_frame = cv2.merge([(spot_color[2]*ai_frame).astype(np.uint8), (spot_color[1]*ai_frame).astype(np.uint8), (spot_color[0]*ai_frame).astype(np.uint8)])
                frame3 = cv2.addWeighted(cv2.subtract(frame1, ai_frame), 0.6, ai_frame, 1.0, 0)
                frame3 = cv2.putText(frame3, 'A', (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 18, cv2.LINE_AA)
                frame3 = cv2.putText(frame3, 'A', (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3, cv2.LINE_AA)
                frame3 = cv2.putText(frame3, 'c:{}'.format(area_avg), (40, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 12, cv2.LINE_AA)
                frame3 = cv2.putText(frame3, 'c:{}'.format(area_avg), (40, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
                if len(contours) > 0:
                    for contour in contours:
                        x, y, w, h = cv2.boundingRect(contour)
                        cv2.rectangle(frame3, (x, y), (x + w, y + h), (0, 0, 255), 4)
            else:
                self.histo_l.opacity = 0
                frame2_thr = cv2.merge([(spot_color[2]*frame2_thr).astype(np.uint8), (spot_color[1]*frame2_thr).astype(np.uint8), (spot_color[0]*frame2_thr).astype(np.uint8)])
                frame3 = cv2.addWeighted(cv2.subtract(frame1, frame2_thr), 0.6, frame2_thr, 1.0, 0)
            #(B, G, R) = cv2.split(frame2[1])
            #zero_arr = np.zeros(B.shape, dtype = uint8)
            #frame2 = cv2.merge([R*0,G,B])
            
            buf1 = cv2.flip(frame3, 0)
            buf = buf1.tobytes()
            texture = Texture.create(size=(frame1.shape[1], frame1.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.canva.texture = texture
            try:
                if temp_celsius:
                    self.temp = self.dht_device.temperature
                    if self.temp == None:
                        self.temp = -1
                else:
                    self.temp = self.dht_device.temperature*(9/5)+32
                self.humidity = self.dht_device.humidity
                if self.humidity == None:
                    self.humidity = -1
            except:
                self.temp = -1
                self.humidity = -1
    
    def count_histo(self, frame):
        if frame.shape != (480, 640):
            raise('Input array mismatch! - Histo')
        hist = cv2.calcHist([frame], [0], None, [50], (0,106), False)
        hist_z = np.zeros(50, dtype = int)
        for i in range(len(hist)):
            try:
                hist_z[i] = np.log10((hist[i][0]))
                #hist_z[i] = int(hist[i][0]/hist[0][0]*100)
            except:
                pass
        return hist_z
        
    def update_debouce(self, dt):
        global debounce
        debounce = 0
    
    def detect_swipe(self, instance, touch):
        if self.manager.current ==  'main':
            if touch.dx > 50:
                self.manager.transition.direction = 'right'
                self.showhide(0)
            if touch.dx < -50:
                self.manager.transition.direction = 'right'
                self.showhide(1)
            if touch.dy > 100:
                self.manager.transition.direction = 'up'
                self.manager.current = "gallery"
            
    def showhide(self, show):
        global menu_visibility
        if debug == 1:
            print("Show/hide event")
        if show == 0:
            if menu_visibility:  
                anim = Animation(pos_hint = {"right": 2}, d = 0.5, t = "in_out_sine")
                anim2 = Animation(pos_hint = {"x": .1}, d = 0.5, t = "in_out_sine")
                anim.start(self.mode_button)
                anim.start(self.thr_button)
                anim.start(self.ai_button)
                anim.start(self.shot_button)
                anim.start(self.settings_button)
                anim2.start(self.canva)
                menu_visibility = False
        if show == 1:
            if menu_visibility == False: 
                anim = Animation(pos_hint = {"right": 1}, d = 0.5, t = "in_out_sine")
                anim2 = Animation(pos_hint = {"x": .05}, d = 0.5, t = "in_out_sine")
                anim.start(self.mode_button)
                anim.start(self.thr_button)
                anim.start(self.ai_button)
                anim.start(self.shot_button)
                anim.start(self.settings_button)
                anim2.start(self.canva)
                menu_visibility = True
        

    def showmodes(self):
        global modes_visibility
        
        if self.mxmd.pos_hint["right"] > 1:
            self.hide_all_subwidgets()
            anim1 = Animation(pos_hint = {"right": 0.74, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim2 = Animation(pos_hint = {"right": 0.82, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim3 = Animation(pos_hint = {"right": 0.9, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim1.start(self.mxmd)
            anim2.start(self.uvmd)
            anim3.start(self.vsmd)
            modes_visibility = True
        if self.mxmd.pos_hint["right"] < 1:
            anim = Animation(pos_hint = {"right": 1.2, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim.start(self.mxmd)
            anim.start(self.uvmd)
            anim.start(self.vsmd)
            modes_visibility = False
            print(modes_visibility)

    def acceptmodes(self, mode):
        global modes_visibility
        anim = Animation(pos_hint = {"right": 1.2, "top": 0.95}, d = 0.5, t = "in_out_sine")
        modes = [loc_dict['mix_t'], loc_dict['uv_t'], loc_dict['vis_t']]
        self.mode_button.text = "{}:\n{}".format(loc_dict['mode_t'], modes[mode])
        if mode == 0:
            self.thr_button.disabled = False
            self.current_mode = 0
        elif mode == 1:
            self.thr_button.disabled = True
            self.current_mode = 1
        elif mode == 2:
            self.thr_button.disabled = True
            self.current_mode = 2
        anim.start(self.mxmd)
        anim.start(self.uvmd)
        anim.start(self.vsmd)
        modes_visibility = False
        print(mode)

    def showslider(self, slider):
        if debug == 1:
            print("showslider({}) event".format(slider))
        global thr_sl_visibility
        
        anim_show = Animation(pos_hint = {"right": 0.85, "top": 0.98}, d = 0.5, t = "in_out_sine")
        anim_hide = Animation(pos_hint = {"right": 0.85, "top": 2.98}, d = 0.5, t = "in_out_sine")
        if slider == 0:
            if self.thr_slider.pos_hint["top"] > 1:
                self.hide_all_subwidgets()
                anim_show.start(self.thr_slider)
                thr_sl_visibility = True
                self.thr_slider.disabled = False
            if self.thr_slider.pos_hint["top"] < 1:
                anim_hide.start(self.thr_slider)
                thr_sl_visibility = False
                self.thr_slider.disabled = True
        pass

    def update_slider(self, slider):
        global thr_sl_val
        if slider == 0:
            thr_sl_val = self.thr_slider.value
            self.thr_button.text = "{}:\n{}".format(loc_dict['threshold_t'], int(thr_sl_val))

    def hide_all_subwidgets(self):
        global modes_visibility, thr_sl_visibility
        anim = Animation(pos_hint = {"right": 1.2, "top": 0.95}, d = 0.5, t = "in_out_sine")
        anim.start(self.mxmd)
        anim.start(self.uvmd)
        anim.start(self.vsmd)
        anim = Animation(pos_hint = {"right": 0.85, "top": 2.98}, d = 0.5, t = "in_out_sine")
        anim.start(self.thr_slider)
        modes_visibility = False
        thr_sl_visibility = False
        
#     def detect_shot_swipe(self, instance, touch):
#         if touch.dx > 50:
#             pass
#         if touch.dx < -50:
#             print("Changed")
#             self.shot_button.text = next(click_types)

    def shot_clicked(self, instance, touch):
        global debounce
        if debounce == 0:
            debounce = 1
            print(touch.is_double_tap)
            if touch.x > 725 and touch.x < 790:
                if touch.y > 110 and touch.y < 170:
                    print("Short clicked")
            print(touch.x, touch.y)
            
    def accumulate(self, dt):
        self.shot_button.text = '{}/{}'.format(self.acc_counter, acc_period)
        print(self.acc_counter)
        self.acc_counter += 1
        
    def preview(self):
        global preview_data
        if capt_m == 0:
            preview_data = [frame1, frame2, self.current_mode, thr_sl_val, datetime.datetime.now(), self.temp, self.humidity]
        elif capt_m == 1:
            self.acc_counter = 1
            self.frame_acc = np.zeros((480, 640, 3), np.uint8)
            while self.acc_counter <= acc_period:
                #self.frame_acc = cv2.bitwise_xor(self.frame_acc, frame2, mask = None)
                self.frame_acc = ((self.frame_acc + frame2) / 2)
                time.sleep(.5)
                self.acc_counter += 1
            preview_data = [frame1, self.frame_acc, self.current_mode, thr_sl_val, datetime.datetime.now(), self.temp, self.humidity]
            self.shot_button.text = loc_dict['shot_t']
        elif capt_m == 2:
            pass    #### Заглушка для реализации записи видео
        
    def AI_callback(self):
        global Analysis
        global debounce
        if debounce == 0:
            if Analysis:
                Analysis = False
                self.ai_button.text = "{}:\n{}".format(loc_dict['analysis_t'], loc_dict['off_t'])
            else:
                Analysis = True
                self.ai_button.text = "{}:\n{}".format(loc_dict['analysis_t'], loc_dict['on_t'])
            debounce = 1

        
    def on_destroy(self):
        self.video_input1.release()    
        self.video_input2.release()
        self.dht_device.exit()
        result = subprocess.run(['pgrep', 'libgpiod_pulse'], capture_output = True, text = True)
        lines = result.stdout.split('\n')
        for el in lines:
            result = subprocess.run(['kill', el], capture_output = True, text = True)
        print("Capture released!")

class SettingsScreen(Screen):
    def on_enter(self):
        self.settings_layout.clear_widgets()
        self.settings_label.text = loc_dict['settings_verb_t']
        self.lang_button.text = loc_dict['lang_t']
        self.color_picker_button.text = loc_dict['spot_color_t']
        self.capture_mode_button.text = loc_dict['capture_mode_t']
        self.accum_period_button.text = loc_dict['accum_shot_t']
        self.temp_unit_button.text = loc_dict['temp_unit_t']
        self.save_mode_button.text = loc_dict['save_mode_t']
        self.date_time_button.text = loc_dict['date_time_t']
        self.about_button.text = loc_dict['about_t']
        self.dev_mode_button.text = loc_dict['dev_mode_t']
        self.return_button.text = loc_dict['return_t']
    
    def lang_button_pressed(self):
        global cnfgprs, language
        if language == 1:
            l_state = ['down', 'normal']
        else:
            l_state = ['normal','down']
        self.settings_layout.clear_widgets()
        self.settings_label.text = '{}:'.format(loc_dict['lang_t'])
        self.eng_lang = ToggleButton(text='English', group='Lang', state=l_state[0], size_hint = [.8, .4], pos_hint = {'center_x': .5})
        self.rus_lang = ToggleButton(text='Русский', group='Lang', state=l_state[1], size_hint = [.8, .4], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.eng_lang)
        self.settings_layout.add_widget(self.rus_lang)
        self.eng_lang.bind(on_press = self.change_lang)
        self.rus_lang.bind(on_press = self.change_lang)

    def change_lang(self, instance):
        global debounce, language, loc_dict
        if debounce == 0:
            debounce = 1
            if self.eng_lang.state == 'down':
                print('eng')
                language = 1
                self.rus_lang.state = 'normal'
                self.eng_lang.state = 'down'
                cnfgprs['COMMON']['language'] = '1'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            elif self.rus_lang.state == 'down':
                print('rus')
                language = 0
                self.eng_lang.state = 'normal'
                self.rus_lang.state = 'down'
                cnfgprs['COMMON']['language'] = '0'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            if language == 1:
                loc_dict = localeprs['ENG']
            elif language == 0:
                loc_dict = localeprs['RUS']
            self.settings_label.text = loc_dict['lang_t']
            self.lang_button.text = loc_dict['lang_t']
            self.color_picker_button.text = loc_dict['spot_color_t']
            self.capture_mode_button.text = loc_dict['capture_mode_t']
            self.accum_period_button.text = loc_dict['accum_shot_t']
            self.temp_unit_button.text = loc_dict['temp_unit_t']
            self.save_mode_button.text = loc_dict['save_mode_t']
            self.date_time_button.text = loc_dict['date_time_t']
            self.about_button.text = loc_dict['about_t']
            self.dev_mode_button.text = loc_dict['dev_mode_t']
            self.return_button.text = loc_dict['return_t']
    
    def color_button_pressed(self):
        global spot_color
        self.settings_layout.clear_widgets()
        self.settings_label.text = loc_dict['spot_color_verb_t']
        self.color_mixer = ColorMixer()
        self.red_picker = Slider(orientation='horizontal', min=0, max=1, value=spot_color[0], value_track=True, value_track_color=[1,0,0,1])
        self.green_picker = Slider(orientation='horizontal', min=0, max=1, value=spot_color[1], value_track=True, value_track_color=[0,1,0,1])
        self.blue_picker = Slider(orientation='horizontal', min=0, max=1, value=spot_color[2], value_track=True, value_track_color=[0,0,1,1])
        self.red_picker.bind(value = self.on_slider_value)
        self.green_picker.bind(value = self.on_slider_value)
        self.blue_picker.bind(value = self.on_slider_value)
        self.accept_button = Button(text = loc_dict['accept_t'], size_hint = [.4, .3], pos_hint = {'center_x': .5, 'top':1}) 
        self.accept_button.bind(on_press = self.accept_spot_color)
        self.settings_layout.add_widget(self.color_mixer)
        self.settings_layout.add_widget(self.red_picker)
        self.settings_layout.add_widget(self.green_picker)
        self.settings_layout.add_widget(self.blue_picker)
        self.settings_layout.add_widget(self.accept_button)
        
    def accept_spot_color(self, instance):
        global cnfgprs
        cnfgprs['APPEARANCE']['spot_r'] = str(self.red_picker.value)
        cnfgprs['APPEARANCE']['spot_g'] = str(self.green_picker.value)
        cnfgprs['APPEARANCE']['spot_b'] = str(self.blue_picker.value)
        with open('global.ini', 'w') as configfile:
            cnfgprs.write(configfile)

    def on_slider_value(self, instance, value):
        global spot_color
        self.color_mixer.update_color(self.red_picker.value,  self.green_picker.value,  self.blue_picker.value)
        spot_color[0] = self.red_picker.value
        spot_color[1] = self.green_picker.value
        spot_color[2] = self.blue_picker.value

    def capture_mode_pressed(self):
        global cnfgprs, capt_m
        if capt_m == 0:
            cm_state = ['down', 'normal', 'normal']
        elif capt_m == 1:
            cm_state = ['normal','down', 'normal']
        else:
            cm_state = ['normal', 'normal','down']
        self.settings_layout.clear_widgets()
        self.settings_label.text = loc_dict['capture_mode_verb_t']
        self.shot = ToggleButton(text=loc_dict['one_shot_t'], group='Capture', state=cm_state[0], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.accum = ToggleButton(text=loc_dict['accum_shot_t'], group='Capture', state=cm_state[1], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.video = ToggleButton(text=loc_dict['video_t'], group='Capture', state=cm_state[2], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.shot)
        self.settings_layout.add_widget(self.accum)
        #self.settings_layout.add_widget(self.video)       ###Заглушка для видео
        self.shot.bind(on_press = self.change_cm)
        self.accum.bind(on_press = self.change_cm)
        #self.video.bind(on_press = self.change_cm)        ###Заглушка для видео

    def change_cm(self, instance):
        global debounce, capt_m
        if debounce == 0:
            debounce = 1
            if self.shot.state == 'down':
                print('shot')
                capt_m = 0
                self.accum.state = 'normal'
                self.video.state = 'normal'
                cnfgprs['MODES']['capture_m'] = '0'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            elif self.accum.state == 'down':
                print('accum')
                capt_m = 1
                self.shot.state = 'normal'
                self.video.state = 'normal'
                cnfgprs['MODES']['capture_m'] = '1'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            elif self.video.state == 'down':
                print('video')
                capt_m = 2
                self.shot.state = 'normal'
                self.accum.state = 'normal'
                cnfgprs['MODES']['capture_m'] = '2'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
    #int(cnfgprs['MODES']['capture_m'])
        
    def accum_period_pressed(self):
        global cnfgprs, acc_period
        self.settings_layout.clear_widgets()
        self.settings_label.text = loc_dict['accum_period_verb_t']
        self.accum_slider = Slider(orientation='horizontal', min=2, max=20, value=acc_period, value_track=True, value_track_color=[.9,.3,.3,1])
        self.accum_label = Label(text='{} {}'.format(str(int(self.accum_slider.value)), loc_dict['accum_period_frames_t']), size_hint = [1, .1], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.accum_label)
        self.settings_layout.add_widget(self.accum_slider)
        self.accum_slider.bind(value = self.change_acc_period)
        
    def change_acc_period(self, instance, value):
        global acc_period
        value = int(value)
        acc_period = value
        self.accum_label.text = '{} {}'.format(str(int(self.accum_slider.value)), loc_dict['accum_period_frames_t'])
        cnfgprs['APPEARANCE']['acc_period'] = str(value)
        with open('global.ini', 'w') as configfile:
            cnfgprs.write(configfile)
            
    def temp_unit_pressed(self):
        global cnfgprs, temp_u
        if temp_u == 0:
            tu_state = ['down', 'normal']
        else:
            tu_state = ['normal','down']
        self.settings_layout.clear_widgets()
        self.settings_label.text = loc_dict['temp_unit_t']
        self.cels = ToggleButton(text=loc_dict['celsius_t'], group='Temperature', state=tu_state[0], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.fahren = ToggleButton(text=loc_dict['fahrengate_t'], group='Temperature', state=tu_state[1], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        if self.cels.state == 'down':
            self.temp_label = Label(text=u'{} 23\u00B0C'.format(loc_dict['temp_unit_verb_t']), size_hint = [1, .1], pos_hint = {'center_x': .5})
        if self.fahren.state == 'down':
            self.temp_label = Label(text=u'{} 73.4\u00B0F'.format(loc_dict['temp_unit_verb_t']), size_hint = [1, .1], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.temp_label)
        self.settings_layout.add_widget(self.cels)
        self.settings_layout.add_widget(self.fahren)
        self.cels.bind(on_press = self.change_tu)
        self.fahren.bind(on_press = self.change_tu)
        
    def change_tu(self, instance):
        global debounce, temp_u
        if debounce == 0:
            debounce = 1
            if self.cels.state == 'down':
                print('cels')
                temp_u = 0
                self.temp_label.text = u'{} 23\u00B0C'.format(loc_dict['temp_unit_verb_t'])
                self.fahren.state = 'normal'
                cnfgprs['APPEARANCE']['temp_u'] = '0'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            else:
                print('fahren')
                temp_u = 1
                self.temp_label.text = u'{} 73.4\u00B0F'.format(loc_dict['temp_unit_verb_t'])
                self.cels.state = 'normal'
                cnfgprs['APPEARANCE']['temp_u'] = '1'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
        
    def save_mode_pressed(self):
        global cnfgprs, save_m
        if save_m == 0:
            sm_state = ['down', 'normal']
        else:
            sm_state = ['normal','down']
        self.settings_layout.clear_widgets()
        self.settings_label.text = '{}\n{}\n{}\n{}'.format(loc_dict['save_mode_verb_t'].split('!')[0], loc_dict['save_mode_verb_t'].split('!')[1], loc_dict['save_mode_verb_t'].split('!')[2], loc_dict['save_mode_verb_t'].split('!')[3])
        self.pic = ToggleButton(text=loc_dict['image_t'], group='Save mode', state=sm_state[0], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.full = ToggleButton(text=loc_dict['full_t'], group='Save mode', state=sm_state[1], size_hint = [.6, .2], pos_hint = {'center_x': .5}) 
        self.settings_layout.add_widget(self.pic)
        self.settings_layout.add_widget(self.full)
        self.pic.bind(on_press = self.change_sm)
        self.full.bind(on_press = self.change_sm)
        
    def change_sm(self, instance):
        global debounce, save_m
        if debounce == 0:
            debounce = 1
            if self.pic.state == 'down':
                save_m = 0
                self.full.state = 'normal'
                cnfgprs['MODES']['save_m'] = '0'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            else:
                save_m = 1
                self.pic.state = 'normal'
                cnfgprs['MODES']['save_m'] = '1'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
    
    def dev_mode_pressed(self):
        self.settings_layout.clear_widgets()
        self.settings_label.text = '{}\n{}'.format(loc_dict['dev_mode_verb_t'].split('!')[0], loc_dict['dev_mode_verb_t'].split('!')[1])
               
        self.pin_layout = BoxLayout(orientation = 'vertical', spacing = 5)
               
        self.pin_label = Label(text = 'PIN:', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .5, 'top': 1})
        self.pin_input = TextInput(text = '****', size_hint = [None, None], size = [80, 30], pos_hint = {'center_x': .5, 'center_y': 0.5})
        self.accept = Button(text = loc_dict['accept_t'], size_hint = [None, None], size = [100, 50], pos_hint = {'center_x': .5, 'center_y':0.3})
        self.spacing = Label(size_hint = [1, None], size = [40,120])
        self.accept.bind(on_press = self.check_password)
        
        
        self.pin_layout.add_widget(self.pin_label)
        self.pin_layout.add_widget(self.pin_input)
        self.pin_layout.add_widget(self.spacing)
        self.pin_layout.add_widget(self.accept)
        self.settings_layout.add_widget(self.pin_layout)
        
    def check_password(self, *args):
        entered_password = self.pin_input.text.encode('utf-8')
        hashed_password = hashlib.sha256(entered_password).hexdigest()
        if hashed_password == hash_etalon:
            self.spacing.text = 'Ok!'                                    #Localisation
            devmodeprs['panel']['widgets_left'] = 'smenu window-list'
            with open('/home/filin/.config/wf-panel-pi.ini', 'w') as panelfile:
                devmodeprs.write(panelfile)
        else:
            self.spacing.text = 'Wrong password!'
        
    def datetime_pressed(self):
        date = datetime.datetime.strftime(datetime.datetime.now(), '%d %m 20%y %H %M').split(' ')
        self.settings_layout.clear_widgets()
        self.settings_label.text = loc_dict['date_time_t']
        self.date_layout = BoxLayout(orientation = 'horizontal')
        
        self.day_layout = BoxLayout(orientation = 'vertical')
        self.month_layout = BoxLayout(orientation = 'vertical')
        self.year_layout = BoxLayout(orientation = 'vertical')
        self.hour_layout = BoxLayout(orientation = 'vertical')
        self.min_layout = BoxLayout(orientation = 'vertical')
        self.spacer = BoxLayout(orientation = 'vertical', padding = 20)
               
        self.day_up = Button(text = '+D', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .9, 'top': 1.0})
        self.day_label = Label(text = date[0], size_hint = [None, None], size = [50, 50], pos_hint = {'center_x': .9, 'center_y': .5})
        self.day_down = Button(text = '-D', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .9, 'center_y': .4})
        self.month_up = Button(text = '+M', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .5, 'center_y': .6})
        self.month_label = Label(text = date[1], size_hint = [None, None], size = [50, 50], pos_hint = {'center_x': .5, 'center_y': .6})
        self.month_down = Button(text = '-M', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .5, 'center_y': .6})
        self.year_up = Button(text = '+Y', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .1, 'center_y': .6})
        self.year_label = Label(text = date[2], size_hint = [None, None], size = [50, 50], pos_hint = {'center_x': .1, 'center_y': .6})
        self.year_down = Button(text = '-Y', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .1, 'center_y': .6})
        
        self.hour_up = Button(text = '+h', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .6, 'center_y': .6})
        self.hour_label = Label(text = date[3], size_hint = [None, None], size = [50, 50], pos_hint = {'center_x': .6, 'center_y': .6})
        self.hour_down = Button(text = '-h', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .6, 'center_y': .6})
        self.min_up = Button(text = '+m', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .1, 'center_y': .6})
        self.min_label = Label(text = date[4], size_hint = [None, None], size = [50, 50], pos_hint = {'center_x': .1, 'center_y': .6})
        self.min_down = Button(text = '-m', size_hint = [None, None], size = [40, 40], pos_hint = {'center_x': .1, 'center_y': .6})
         
        self.accept = Button(text = loc_dict['accept_t'], size_hint = [None, None], size = [80, 50], pos_hint = {'center_x': .5})
        
        self.day_up.bind(on_press = self.datetime_button_pressed)
        self.day_down.bind(on_press = self.datetime_button_pressed)
        self.month_up.bind(on_press = self.datetime_button_pressed)
        self.month_down.bind(on_press = self.datetime_button_pressed)
        self.year_up.bind(on_press = self.datetime_button_pressed)
        self.year_down.bind(on_press = self.datetime_button_pressed)
        self.hour_up.bind(on_press = self.datetime_button_pressed)
        self.hour_down.bind(on_press = self.datetime_button_pressed)
        self.min_up.bind(on_press = self.datetime_button_pressed)
        self.min_down.bind(on_press = self.datetime_button_pressed)
        self.accept.bind(on_press = self.datetime_button_pressed)
        
        self.settings_layout.add_widget(self.date_layout)
        self.settings_layout.add_widget(self.spacer)
        self.spacer.add_widget(self.accept)

        self.date_layout.add_widget(self.day_layout)
        self.date_layout.add_widget(self.month_layout)
        self.date_layout.add_widget(self.year_layout)
        self.date_layout.add_widget(self.hour_layout)
        self.date_layout.add_widget(self.min_layout)
        
        self.day_layout.add_widget(self.day_up)
        self.day_layout.add_widget(self.day_label)
        self.day_layout.add_widget(self.day_down)
        
        
        self.month_layout.add_widget(self.month_up)
        self.month_layout.add_widget(self.month_label)
        self.month_layout.add_widget(self.month_down)
        
        self.year_layout.add_widget(self.year_up)
        self.year_layout.add_widget(self.year_label)
        self.year_layout.add_widget(self.year_down)
        
        self.hour_layout.add_widget(self.hour_up)
        self.hour_layout.add_widget(self.hour_label)
        self.hour_layout.add_widget(self.hour_down)
        
        self.min_layout.add_widget(self.min_up)
        self.min_layout.add_widget(self.min_label)
        self.min_layout.add_widget(self.min_down)
    
    def datetime_button_pressed(self, instance, *args):
        if instance.text == '+D':
            if int(self.day_label.text) < 31:
                self.day_label.text = '{:02d}'.format(int(self.day_label.text) + 1)
            else:
                self.day_label.text = '01'
        if instance.text == '-D':
            if int(self.day_label.text) > 1:
                self.day_label.text = '{:02d}'.format(int(self.day_label.text) - 1)
            else:
                self.day_label.text = '31'
        if instance.text == '+M':
            if int(self.month_label.text) < 12:
                self.month_label.text = '{:02d}'.format(int(self.month_label.text) + 1)
            else:
                self.month_label.text = '01'
        if instance.text == '-M':
            if int(self.month_label.text) > 1:
                self.month_label.text = '{:02d}'.format(int(self.month_label.text) - 1)
            else:
                self.month_label.text = '12'
        if instance.text == '+Y':
            if int(self.year_label.text) < 2100:
                self.year_label.text = '{:04d}'.format(int(self.year_label.text) + 1)
            else:
                self.year_label.text = '2020'
        if instance.text == '-Y':
            if int(self.year_label.text) > 2020:
                self.year_label.text = '{:04d}'.format(int(self.year_label.text) - 1)
            else:
                self.year_label.text = '2100'
        if instance.text == '+h':
            if int(self.hour_label.text) < 23:
                self.hour_label.text = '{:02d}'.format(int(self.hour_label.text) + 1)
            else:
                self.hour_label.text = '00'
        if instance.text == '-h':
            if int(self.hour_label.text) > 0:
                self.hour_label.text = '{:02d}'.format(int(self.hour_label.text) - 1)
            else:
                self.hour_label.text = '23'
        if instance.text == '+m':
            if int(self.min_label.text) < 59:
                self.min_label.text = '{:02d}'.format(int(self.min_label.text) + 1)
            else:
                self.min_label.text = '00'
        if instance.text == '-m':
            if int(self.min_label.text) > 0:
                self.min_label.text = '{:02d}'.format(int(self.min_label.text) - 1)
            else:
                self.min_label.text = '59'
        if instance.text == loc_dict['accept_t']:
            accept_date = '{}-{}-{} {}:{}:00'.format(self.year_label.text,
                                                     self.month_label.text,
                                                     self.day_label.text,
                                                     self.hour_label.text,
                                                     self.min_label.text)
            res = subprocess.run(['sudo','timedatectl','set-time', accept_date], capture_output = True)
        
#         
class ColorMixer(Widget):
    def __init__(self, **kwargs):
        super(ColorMixer,self).__init__(**kwargs)
        self.bind(pos=self.update_rect, size=self.update_rect)
        with self.canvas:
            self.color = Color(spot_color[0],spot_color[1],spot_color[2],1)
            self.rect = Rectangle()
        
    def update_color(self, *args):
        self.color.rgba = (args[0], args[1], args[2],1)
        
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

class ViewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.view_canva.bind(on_touch_move=self.detect_swipe)
        self.zoomK = 1
        self.dx = 0
        self.dy = 0
        
    def on_enter(self):
        self.frame1 = frame1
        self.frame2 = frame2
        self.render()
        self.check_memorycard()
        self.info_button.text = loc_dict['info_t']
        self.zoom_button.text = loc_dict['zoom_t']
        self.save_button.text = loc_dict['save_t']
        self.cancel_button.text = loc_dict['cancel_t']
        
    def detect_swipe(self, instance, touch):
        if self.manager.current == 'view':
            self.dx = self.dx + int(touch.dx)
            self.dy = self.dy + int(touch.dy)
            self.render()
           
    def render(self):
        if preview_data[2] == 0:
            gr = cv2.cvtColor(self.frame2, cv2.COLOR_BGR2GRAY)
            if capt_m == 0:
                self.frame2_thr = cv2.threshold(gr, 255 - thr_sl_val, 255, cv2.THRESH_BINARY)[1]
            elif capt_m == 1:
                self.frame2_thr = cv2.threshold(gr, 5, 255, cv2.THRESH_TOZERO)[1]
            elif capt_m == 2:
                pass
            self.frame2_thr = cv2.merge([(spot_color[2]*self.frame2_thr).astype(np.uint8), (spot_color[1]*self.frame2_thr).astype(np.uint8), (spot_color[0]*self.frame2_thr).astype(np.uint8)])
            frame3 = cv2.addWeighted(cv2.subtract(self.frame1, self.frame2_thr), 0.6, self.frame2_thr, 1.0, 0)
            self.frame3 = frame3
            self.frame3 = cv2.putText(self.frame3, '{}'.format(datetime.datetime.strftime(preview_data[4], '%d.%m.%y %H:%M:%S')), (50, 450), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                
            datetime.datetime.strftime(preview_data[4], '%d.%m.%y %H:%M:%S')
            if self.zoomK == 1:
                x0 = 0
                y0 = 0
                x1 = 640
                y1 = 480
            elif self.zoomK == 2:
                x0 = 160 - self.dx
                y0 = 120 + self.dy
                x1 = 480 - self.dx
                y1 = 360 + self.dy
                if x0 < 0:
                    self.dx = 160
                    x0 = 0
                    x1 = 320
                if y0 < 0:
                    self.dy = -120
                    y0 = 0
                    y1 = 240
                if x0 > 320:
                    self.dx = -160
                    x0 = 320
                    x1 = 640
                if y0 > 240:
                    self.dy = 120
                    y0 = 240
                    y1 = 480
                
            elif self.zoomK == 4:
                x0 = 240 - self.dx
                y0 = 180 + self.dy
                x1 = 400 - self.dx
                y1 = 300 + self.dy
                if x0 < 0:
                    self.dx = 240
                    x0 = 0
                    x1 = 160
                if y0 < 0:
                    #self.dy = -180
                    y0 = 0
                    y1 = 140
                if x0 > 480:
                    #self.dx = -240
                    x0 = 480
                    x1 = 640
                if y0 > 360:
                    #self.dy = 180
                    y0 = 360
                    y1 = 480    
            zoomed_frame = frame3[y0:y1, x0:x1, :]
            zoomed_frame = cv2.resize(zoomed_frame, (640, 480), interpolation = cv2.INTER_AREA)
            buf1 = cv2.flip(zoomed_frame, 0)
            buf = buf1.tobytes()
            self.texture = Texture.create(size=(zoomed_frame.shape[1], zoomed_frame.shape[0]), colorfmt='bgr')
            self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.view_canva.texture = self.texture
            
            mini_frame = cv2.resize(frame3, (128, 96), interpolation = cv2.INTER_AREA)
            mini_frame = cv2.rectangle(mini_frame, (int(x0/5), int(y0/5)), (int(x1/5), int(y1/5)), (0, 0, 255), 2)
            buf2 = cv2.flip(mini_frame, 0)
            buf = buf2.tobytes()
            self.texture = Texture.create(size=(mini_frame.shape[1], mini_frame.shape[0]), colorfmt='bgr')
            self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.miniature_canva.texture = self.texture
            
        elif preview_data[2] == 1:
            if self.zoomK == 1:
                x0 = 0
                y0 = 0
                x1 = 640
                y1 = 480
            elif self.zoomK == 2:
                x0 = 160 - self.dx
                y0 = 120 + self.dy
                x1 = 480 - self.dx
                y1 = 360 + self.dy
                if x0 < 0:
                    self.dx = 160
                    x0 = 0
                    x1 = 320
                if y0 < 0:
                    self.dy = -120
                    y0 = 0
                    y1 = 240
                if x0 > 320:
                    self.dx = -160
                    x0 = 320
                    x1 = 640
                if y0 > 240:
                    self.dy = 120
                    y0 = 240
                    y1 = 480
                
            elif self.zoomK == 4:
                x0 = 240 - self.dx
                y0 = 180 + self.dy
                x1 = 400 - self.dx
                y1 = 300 + self.dy
                if x0 < 0:
                    self.dx = 240
                    x0 = 0
                    x1 = 160
                if y0 < 0:
                    #self.dy = -180
                    y0 = 0
                    y1 = 140
                if x0 > 480:
                    #self.dx = -240
                    x0 = 480
                    x1 = 640
                if y0 > 360:
                    #self.dy = 180
                    y0 = 360
                    y1 = 480    
            zoomed_frame = self.frame2[y0:y1, x0:x1, :]
            zoomed_frame = cv2.resize(zoomed_frame, (640, 480), interpolation = cv2.INTER_AREA)
            buf1 = cv2.flip(zoomed_frame, 0)
            buf = buf1.tobytes()
            self.texture = Texture.create(size=(zoomed_frame.shape[1], zoomed_frame.shape[0]), colorfmt='bgr')
            self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.view_canva.texture = self.texture
            
            mini_frame = cv2.resize(self.frame2, (128, 96), interpolation = cv2.INTER_AREA)
            mini_frame = cv2.rectangle(mini_frame, (int(x0/5), int(y0/5)), (int(x1/5), int(y1/5)), (0, 0, 255), 2)
            buf2 = cv2.flip(mini_frame, 0)
            buf = buf2.tobytes()
            self.texture = Texture.create(size=(mini_frame.shape[1], mini_frame.shape[0]), colorfmt='bgr')
            self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.miniature_canva.texture = self.texture
            
        elif preview_data[2] == 2:
            if self.zoomK == 1:
                x0 = 0
                y0 = 0
                x1 = 640
                y1 = 480
            elif self.zoomK == 2:
                x0 = 160 - self.dx
                y0 = 120 + self.dy
                x1 = 480 - self.dx
                y1 = 360 + self.dy
                if x0 < 0:
                    self.dx = 160
                    x0 = 0
                    x1 = 320
                if y0 < 0:
                    self.dy = -120
                    y0 = 0
                    y1 = 240
                if x0 > 320:
                    self.dx = -160
                    x0 = 320
                    x1 = 640
                if y0 > 240:
                    self.dy = 120
                    y0 = 240
                    y1 = 480
                
            elif self.zoomK == 4:
                x0 = 240 - self.dx
                y0 = 180 + self.dy
                x1 = 400 - self.dx
                y1 = 300 + self.dy
                if x0 < 0:
                    self.dx = 240
                    x0 = 0
                    x1 = 160
                if y0 < 0:
                    #self.dy = -180
                    y0 = 0
                    y1 = 140
                if x0 > 480:
                    #self.dx = -240
                    x0 = 480
                    x1 = 640
                if y0 > 360:
                    #self.dy = 180
                    y0 = 360
                    y1 = 480    
            zoomed_frame = self.frame1[y0:y1, x0:x1, :]
            zoomed_frame = cv2.resize(zoomed_frame, (640, 480), interpolation = cv2.INTER_AREA)
            buf1 = cv2.flip(zoomed_frame, 0)
            buf = buf1.tobytes()
            self.texture = Texture.create(size=(zoomed_frame.shape[1], zoomed_frame.shape[0]), colorfmt='bgr')
            self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.view_canva.texture = self.texture
            
            mini_frame = cv2.resize(self.frame1, (128, 96), interpolation = cv2.INTER_AREA)
            mini_frame = cv2.rectangle(mini_frame, (int(x0/5), int(y0/5)), (int(x1/5), int(y1/5)), (0, 0, 255), 2)
            buf2 = cv2.flip(mini_frame, 0)
            buf = buf2.tobytes()
            self.texture = Texture.create(size=(mini_frame.shape[1], mini_frame.shape[0]), colorfmt='bgr')
            self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.miniature_canva.texture = self.texture

    def preview_info(self):
        global info_flag, debounce
        if debounce == 0:
            if info_flag == False:
                self.zoom_button.disabled = True
                date = datetime.datetime.strftime(preview_data[4], '%d.%m.%y %H:%M:%S')
                if preview_data[2] == 2:
                    mode_str = 'VIS'
                elif preview_data[2] == 1:
                    mode_str = 'UV'
                elif preview_data[2] == 0:
                    mode_str = 'MIX'
                name = mode_str + '-' + datetime.datetime.strftime(preview_data[4], '%d-%m-%y-%H-%M-%S')
    #             self.name_frame = name
                if preview_data[2] == 0:
                    threshold = round(preview_data[3], 0)
                else:
                    threshold = 0
                if temp_celsius:
                    temp = 'Temperature:{:.1f}C'.format(preview_data[5])
                else:
                    temp = 'Temperature:{:.1f}F'.format(preview_data[5])
                blank = np.zeros((480, 640, 3), np.uint8)
                blank = cv2.putText(blank, 'File name: {}'.format( name), (0, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Date: {}'.format(date), (0, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Mode: {}'.format(mode_str), (0, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Threshold {}'.format(threshold), (0, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, temp, (0, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Humidity: {}%'.format(preview_data[6]), (0, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                buf1 = cv2.flip(blank, 0)
                buf = buf1.tobytes()
                self.info_texture = Texture.create(size=(blank.shape[1], blank.shape[0]), colorfmt='bgr')
                self.info_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
                self.view_canva.texture = self.info_texture
                info_flag = True
            else:
                self.zoom_button.disabled = False
                self.view_canva.texture = self.texture
                info_flag = False
            debounce = 1
        
    def zoom_callback(self):
        global debounce
        if debounce == 0:
            self.zoomK = next(zoomstr)
            self.zoom_button.text = "{}:\n{}x".format(loc_dict['zoom_t'],self.zoomK)
            self.render()
            if self.zoomK == 1:
                self.miniature_canva.opacity = 0
                self.mini_layout.opacity = 0
            else:
                self.miniature_canva.opacity = 1
                self.mini_layout.opacity = 1
            debounce = 1
            
    def check_memorycard(self):
        result = subprocess.run(['lsblk','-o','NAME,MOUNTPOINT,RM,LABEL,UUID,SIZE'], capture_output = True, text = True)
        lines = result.stdout.split('\n')
        for line in lines:
            
            if '/media/' in line:
                parts = re.split(r'\s+', line)
                print(parts[2])
                if parts[2] == '1':
                    print('Memorycard found! path = ', parts[1], 'Total memory = ', parts[4])
                    return parts[1]
        return None
    
    def save_callback(self):
#         anim = Animation(pos_hint = {"center_x": 0.5, "top": 0.5}, d = 0.5, t = "in_out_sine")
#         anim.start(self.loading_bar)
#         self.loading_bar.value = 0
        progressLabel = Label(text='0/100')
        self.loading_popup = Popup(title = 'Saving',
                              content = progressLabel,
                              size_hint = (None, None),
                              size = (300, 100))
        self.loading_popup.open()
        path = self.check_memorycard()
        print(path)
        if path != None:
            if preview_data[2] == 2:
                mode_str = 'VIS'
            elif preview_data[2] == 1:
                mode_str = 'UV'
            elif preview_data[2] == 0:
                mode_str = 'MIX'
            name = mode_str + '-' + datetime.datetime.strftime(preview_data[4], '%d-%m-%y-%H-%M-%S')
            pathjpg = path + '/' + name + '.jpg'
            if preview_data[2] == 2:
                cv2.imwrite(pathjpg, self.frame1)
            elif preview_data[2] == 1:
                cv2.imwrite(pathjpg, self.frame2)
            elif preview_data[2] == 0:
                cv2.imwrite(pathjpg, self.frame3)
            progressLabel.text='20/100'
            if save_all_data:
                root = ET.Element("root")
                
                date_element = ET.SubElement(root, "Date")
                date_element.text  = datetime.datetime.strftime(preview_data[4], '%d-%m-%y %H:%M:%S')

                def add_array_to_xml(parent, array_name, array):
                    channel = ['B','G','R']
                    for i in [0, 1, 2]:
                        print('Saving ', array_name, 'channel ', channel[i])
                        slice_array = array[:,:,i]
                        print(slice_array.shape)
                        array_element = ET.SubElement(parent, array_name)
                        channel_element = ET.SubElement(array_element, channel[i])
                        values_element = ET.SubElement(channel_element, "values")
                        values_text = '\n'.join([';'.join(map(str, row)) for row in slice_array])
                        values_element.text = values_text
                        progressLabel.text='{}/100'.format(20+20*(i+1))


                add_array_to_xml(root, "Visual", self.frame1)
                add_array_to_xml(root, "UV", self.frame2)

                tree = ET.ElementTree(root)
                xml_name = path + '/RAW-' + datetime.datetime.strftime(preview_data[4], '%d-%m-%y-%H-%M-%S') + '.fln'
                tree.write(xml_name, encoding="utf-8", xml_declaration=True)
                progressLabel.text='95/100'
        else:
            layout = GridLayout(cols = 1, padding = 10)
            popupLabel = Label(text = 'Memory card is not found!')
            okButton = Button(text = 'Ok!')
            
            layout.add_widget(popupLabel)
            layout.add_widget(okButton)
            
            popup = Popup(title = 'Error', content = layout, size_hint = (None, None), size = (200, 200))
            popup.open()
            
            okButton.bind(on_press = popup.dismiss)
                
        progressLabel.text='100/100'
        self.loading_popup.dismiss()

class GalleryScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_touch_move=self.detect_swipe)

    def check_memorycard(self):
        result = subprocess.run(['lsblk','-o','NAME,MOUNTPOINT,RM,LABEL,UUID,SIZE'], capture_output = True, text = True)
        lines = result.stdout.split('\n')
        for line in lines:
            
            if '/media/' in line:
                parts = re.split(r'\s+', line)
                print(parts[2])
                if parts[2] == '1':
                    print('Memorycard found! path = ', parts[1], 'Total memory = ', parts[4])
                    return parts[1]
        return None
    
    def load_images(self, path):
        images = [f for f in os.listdir(path) if f.lower().endswith(('.jpg'))]
        return images
            
    def on_enter(self):
        gallery_path = self.check_memorycard()
        if gallery_path == None:
            layout = GridLayout(cols = 1, padding = 10)
            popupLabel = Label(text = 'Memory card is not found!')
            okButton = Button(text = 'Ok!')
            
            layout.add_widget(popupLabel)
            layout.add_widget(okButton)
            
            popup = Popup(title = 'Error', content = layout, size_hint = (None, None), size = (200, 200))
            popup.open()
            
            okButton.bind(on_press = popup.dismiss)
            self.manager.current = "main"
        else:
            images = self.load_images(gallery_path)
            print(images)
            self.scr_view.clear_widgets()
            gallery_layout = GridLayout(rows=2, spacing=25, size_hint = [None, None], orientation = 'tb-lr')
            gallery_layout.bind(minimum_width=gallery_layout.setter('width'))
            for i in images:
                btn = Button(background_normal = gallery_path + '/' + i, text = str(i), size_hint = [None, None], height = 160, width = 213)
                gallery_layout.add_widget(btn)
                btn.bind(on_press = self.show_image)
            self.scr_view.add_widget(gallery_layout)
            
    def show_image(self, instance, *args):
        global gallery_image_path
        gallery_image_path = self.check_memorycard() + '/' + instance.text
        self.manager.current = 'image'
        
    def detect_swipe(self, instance, touch):
        if touch.dy < -100:
            self.manager.transition.direction = 'down'
            self.manager.current = "main"

class ImageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.im_view_canva.bind(on_touch_move=self.detect_swipe)
        self.zoomK = 1
        self.dx = 0
        self.dy = 0
        
    def on_enter(self):
        self.render()
        self.im_zoom_button.text = loc_dict['zoom_t']
        self.im_return_button.text = loc_dict['return_t']

        
    def detect_swipe(self, instance, touch):
        self.dx = self.dx + int(touch.dx)
        self.dy = self.dy + int(touch.dy)
        self.render()
           
    def render(self):
        image = cv2.imread(gallery_image_path)
        if self.zoomK == 1:
            x0 = 0
            y0 = 0
            x1 = 640
            y1 = 480
        elif self.zoomK == 2:
            x0 = 160 - self.dx
            y0 = 120 + self.dy
            x1 = 480 - self.dx
            y1 = 360 + self.dy
            if x0 < 0:
                self.dx = 160
                x0 = 0
                x1 = 320
            if y0 < 0:
                self.dy = -120
                y0 = 0
                y1 = 240
            if x0 > 320:
                self.dx = -160
                x0 = 320
                x1 = 640
            if y0 > 240:
                self.dy = 120
                y0 = 240
                y1 = 480
            
        elif self.zoomK == 4:
            x0 = 240 - self.dx
            y0 = 180 + self.dy
            x1 = 400 - self.dx
            y1 = 300 + self.dy
            if x0 < 0:
                self.dx = 240
                x0 = 0
                x1 = 160
            if y0 < 0:
                #self.dy = -180
                y0 = 0
                y1 = 140
            if x0 > 480:
                #self.dx = -240
                x0 = 480
                x1 = 640
            if y0 > 360:
                #self.dy = 180
                y0 = 360
                y1 = 480    
        zoomed_frame = image[y0:y1, x0:x1, :]
        zoomed_frame = cv2.resize(zoomed_frame, (640, 480), interpolation = cv2.INTER_AREA)
        buf1 = cv2.flip(zoomed_frame, 0)
        buf = buf1.tobytes()
        self.texture = Texture.create(size=(zoomed_frame.shape[1], zoomed_frame.shape[0]), colorfmt='bgr')
        self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.im_view_canva.texture = self.texture
            
        mini_frame = cv2.resize(image, (128, 96), interpolation = cv2.INTER_AREA)
        mini_frame = cv2.rectangle(mini_frame, (int(x0/5), int(y0/5)), (int(x1/5), int(y1/5)), (0, 0, 255), 2)
        buf2 = cv2.flip(mini_frame, 0)
        buf = buf2.tobytes()
        self.texture = Texture.create(size=(mini_frame.shape[1], mini_frame.shape[0]), colorfmt='bgr')
        self.texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.im_miniature_canva.texture = self.texture    
        
    def zoom_callback(self):
        global debounce
        if debounce == 0:
            self.zoomK = next(zoomstr)
            self.im_zoom_button.text = "{}:\n{}x".format(loc_dict['zoom_t'],self.zoomK)
            self.render()
            if self.zoomK == 1:
                self.im_miniature_canva.opacity = 0
                self.im_mini_layout.opacity = 0
            else:
                self.im_miniature_canva.opacity = 1
                self.im_mini_layout.opacity = 1
            debounce = 1
            
            
class FilinApp(App):

    def build(self):
        # Create the screen manager
        sm = ScreenManager()
        sm.add_widget(InitScreen(name='init'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(ViewScreen(name='view'))
        sm.add_widget(GalleryScreen(name='gallery'))
        sm.add_widget(ImageScreen(name='image'))
        return sm

    

if __name__ == '__main__':
    #global language, spot_color, capt_m, acc_period, temp_u, save_m
    cnfgprs.read('global.ini')
    devmodeprs.read('/home/filin/.config/wf-panel-pi.ini')
#     devmodeprs['panel']['widgets_left'] = ''                     #smenu window-list
#     with open('/home/filin/.config/wf-panel-pi.ini', 'w') as panelfile:
#         devmodeprs.write(panelfile)
                    
    language = int(cnfgprs['COMMON']['language'])
    spot_color[0] = float(cnfgprs['APPEARANCE']['spot_r'])
    spot_color[1] = float(cnfgprs['APPEARANCE']['spot_g'])
    spot_color[2] = float(cnfgprs['APPEARANCE']['spot_b'])
    acc_period = int(cnfgprs['APPEARANCE']['acc_period'])
    temp_u = int(cnfgprs['APPEARANCE']['temp_u'])
    capt_m = int(cnfgprs['MODES']['capture_m'])
    save_m = int(cnfgprs['MODES']['save_m'])
    localeprs.read('locale.ini') 
    if language == 1:
        loc_dict = localeprs['ENG']
    elif language == 0:
        loc_dict = localeprs['RUS']
    FilinApp().run()
