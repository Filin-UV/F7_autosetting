from kivy.config import Config
#Config.set('postproc', 'double_tap_time', '10')
from kivy import require
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget

from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
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

require("2.3.0")
debug = 1
video_debug = 0

if debug == 0:
    Window.show_cursor = False
    Window.size = (800, 480)
    Window.borderless = True
else:
    Window.show_cursor = True
    Window.size = (800, 480)
    Window.borderless = False
    Window.resizeable = False
    

#Variables
menu_visibility = True
modes_visibility = False
thr_sl_visibility = False
AI_assistant = False
info_flag = False
temp_celsius = True
area_counter = 0
area = []
area_avg = 0
area_frame_max = 25
thr_sl_val = 200
click_types = cycle(["Shot", "Capture", "Expose"])
zoomstr = cycle([1, 2, 4])
DOUBLE_TAP_TIME = 0.2   # Change time in seconds
LONG_PRESSED_TIME = 0.3  # Change time in seconds
debounce = 0
preview_data = []
frame1 = []
frame2 = []
save_all_data = True

########################GLOBAL SETTINGS################
cnfgprs = configparser.ConfigParser()
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
            camera.release()
        index += 1
    return active_cam


# Declare both screens
class InitScreen(Screen):
    def on_enter(self):
        self.progress_value = 0
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
        self.dht_device = adafruit_dht.DHT22(board.D24, use_pulseio = False)
        
    def update_video(self, dt):
        global area, area_counter, area_avg
        global frame1, frame2
        if video_debug == 0:
            print('!')
            ret1, frame1 = self.video_input1.read()
            ret2, frame2 = self.video_input2.read()
        else:
            frame1 = cv2.imread("res/vis_test.jpg")
            frame2 = cv2.imread("res/uv_test.jpg")
        
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
            if AI_assistant:
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
                frame3 = cv2.putText(frame3, 'AI', (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 18, cv2.LINE_AA)
                frame3 = cv2.putText(frame3, 'AI', (40, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3, cv2.LINE_AA)
                frame3 = cv2.putText(frame3, 'counter:{}'.format(area_avg), (40, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 0, 255), 12, cv2.LINE_AA)
                frame3 = cv2.putText(frame3, 'counter:{}'.format(area_avg), (40, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
                if len(contours) > 0:
                    for contour in contours:
                        x, y, w, h = cv2.boundingRect(contour)
                        cv2.rectangle(frame3, (x, y), (x + w, y + h), (0, 0, 255), 4)
            else:
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
        
    def update_debouce(self, dt):
        global debounce
        debounce = 0
    
    def detect_swipe(self, instance, touch):
        if touch.dx > 50:
            self.showhide(0)
        if touch.dx < -50:
            self.showhide(1)
            
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
        modes = ["Mix", "UV", "VIS"]
        self.mode_button.text = "Mode:\n{}".format(modes[mode])
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
            self.thr_button.text = "Threshold:\n{}".format(int(thr_sl_val))

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
                self.frame_acc = cv2.bitwise_xor(self.frame_acc, frame2, mask = None)
                time.sleep(.5)
                self.acc_counter += 1
            preview_data = [frame1, self.frame_acc, self.current_mode, thr_sl_val, datetime.datetime.now(), self.temp, self.humidity]
            self.shot_button.text = 'Shot'       
        elif capt_m == 2:
            pass
        
    def AI_callback(self):
        global AI_assistant
        global debounce
        if debounce == 0:
            if AI_assistant:
                AI_assistant = False
                self.ai_button.text = "AI assist:\nOff"
            else:
                AI_assistant = True
                self.ai_button.text = "AI assist:\nOn"
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
        self.settings_label.text = 'Choose the category:'
    
    def lang_button_pressed(self):
        global cnfgprs, language
        if language == 1:
            l_state = ['down', 'normal']
        else:
            l_state = ['normal','down']
        self.settings_layout.clear_widgets()
        self.settings_label.text = 'Language:'
        self.eng_lang = ToggleButton(text='English', group='Lang', state=l_state[0], size_hint = [.8, .4], pos_hint = {'center_x': .5})
        self.rus_lang = ToggleButton(text='Русский', group='Lang', state=l_state[1], size_hint = [.8, .4], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.eng_lang)
        self.settings_layout.add_widget(self.rus_lang)
        self.eng_lang.bind(on_press = self.change_lang)
        self.rus_lang.bind(on_press = self.change_lang)

    def change_lang(self, instance):
        global debounce, language
        if debounce == 0:
            debounce = 1
            if self.eng_lang.state == 'down':
                print('eng')
                language = 1
                self.rus_lang.state = 'normal'
                cnfgprs['COMMON']['language'] = '1'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            elif self.rus_lang.state == 'down':
                print('rus')
                language = 0
                self.eng_lang.state = 'normal'
                cnfgprs['COMMON']['language'] = '0'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
    
    def color_button_pressed(self):
        global spot_color
        self.settings_layout.clear_widgets()
        self.settings_label.text = 'Spot color picker:'
        self.color_mixer = ColorMixer()
        self.red_picker = Slider(orientation='horizontal', min=0, max=1, value=spot_color[0], value_track=True, value_track_color=[1,0,0,1])
        self.green_picker = Slider(orientation='horizontal', min=0, max=1, value=spot_color[1], value_track=True, value_track_color=[0,1,0,1])
        self.blue_picker = Slider(orientation='horizontal', min=0, max=1, value=spot_color[2], value_track=True, value_track_color=[0,0,1,1])
        self.red_picker.bind(value = self.on_slider_value)
        self.green_picker.bind(value = self.on_slider_value)
        self.blue_picker.bind(value = self.on_slider_value)
        self.accept_button = Button(text = 'Accept', size_hint = [.4, .3], pos_hint = {'center_x': .5, 'top':1}) 
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
        self.settings_label.text = 'Capture mode:\n Choose the action that will be performed when Shot button pressed'
        self.shot = ToggleButton(text='Shot', group='Capture', state=cm_state[0], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.accum = ToggleButton(text='Accumulated shot', group='Capture', state=cm_state[1], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.video = ToggleButton(text='Video capture', group='Capture', state=cm_state[2], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.shot)
        self.settings_layout.add_widget(self.accum)
        #self.settings_layout.add_widget(self.video)
        self.shot.bind(on_press = self.change_cm)
        self.accum.bind(on_press = self.change_cm)
        #self.video.bind(on_press = self.change_cm)

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
                print('accum')
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
        self.settings_label.text = 'Accumulation pediod:\n Choose UV frames number that will be accumulated to reduce the noise'
        self.accum_slider = Slider(orientation='horizontal', min=2, max=20, value=acc_period, value_track=True, value_track_color=[.9,.3,.3,1])
        self.accum_label = Label(text=str(self.accum_slider.value)+' frames', size_hint = [1, .1], pos_hint = {'center_x': .5})
        self.settings_layout.add_widget(self.accum_label)
        self.settings_layout.add_widget(self.accum_slider)
        self.accum_slider.bind(value = self.change_acc_period)
        
    def change_acc_period(self, instance, value):
        global acc_period
        value = int(value)
        acc_period = value
        self.accum_label.text = str(value)+' frames'
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
        self.settings_label.text = 'Temperature unit:'
        self.cels = ToggleButton(text='Celsius', group='Temperature', state=tu_state[0], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.fahren = ToggleButton(text='Fahrengate', group='Temperature', state=tu_state[1], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        if self.cels.state == 'down':
            self.temp_label = Label(text=u'Example: 23\u00B0C', size_hint = [1, .1], pos_hint = {'center_x': .5})
        if self.fahren.state == 'down':
            self.temp_label = Label(text=u'Example: 73.4\u00B0F', size_hint = [1, .1], pos_hint = {'center_x': .5})
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
                self.temp_label.text=u'Example: 23\u00B0C'
                self.fahren.state = 'normal'
                cnfgprs['APPEARANCE']['temp_u'] = '0'
                with open('global.ini', 'w') as configfile:
                    cnfgprs.write(configfile)
            else:
                print('fahren')
                temp_u = 1
                self.temp_label.text=u'Example: 73.4\u00B0F'
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
        self.settings_label.text = 'Save mode:\n Select which files will be saved when you click on the Shot button:\n - Image - Only the image in the selected display mode\n - Full - An Image and a full data set in the format .fln for post-processing \n in desktop sowtware'
        self.pic = ToggleButton(text='Image', group='Save mode', state=sm_state[0], size_hint = [.6, .2], pos_hint = {'center_x': .5})
        self.full = ToggleButton(text='Full', group='Save mode', state=sm_state[1], size_hint = [.6, .2], pos_hint = {'center_x': .5}) 
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
        
    def brightness_pressed(self):
        self.settings_layout.clear_widgets()
        self.settings_label.text = 'Brightness:\n Adjust screen brightness for comfortable operation with the device'
        self.brightness_slider = Slider(orientation='horizontal', min=5, max=100, step=1, value=85, value_track=True, value_track_color=[.9,.3,.3,1])
        self.brightness_label = Label(text=str(self.brightness_slider.value)+'%', size_hint = [1, .1], pos_hint = {'center_x': .5})
        self.brightness_slider.bind(on_touch_move = self.brightness_refresh)
        self.settings_layout.add_widget(self.brightness_label)
        self.settings_layout.add_widget(self.brightness_slider)
        
    def brightness_refresh(self, *args):
        self.current_brightness =  int(self.brightness_slider.value)
        self.current_brightness_normalized = int(self.current_brightness * 2.55)
        res = subprocess.run(['sudo','echo',str(self.current_brightness_normalized),'|','sudo', 'tee', '/sys/class/backlight/*/brightness'], capture_output = True)
        print(res)
        self.brightness_label.text = str(self.brightness_slider.value)+'%'
        
        
    def datetime_pressed(self):
        date = datetime.datetime.strftime(datetime.datetime.now(), '%d %m 20%y %H %M').split(' ')
        self.settings_layout.clear_widgets()
        self.settings_label.text = 'Date & Time:'
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
         
        self.accept = Button(text = 'Accept', size_hint = [None, None], size = [80, 50], pos_hint = {'center_x': .5})
        
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
        if instance.text == 'Accept':
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
        
    def detect_swipe(self, instance, touch):
        self.dx = self.dx + int(touch.dx)
        self.dy = self.dy + int(touch.dy)
        self.render()
           
    def render(self):
        if preview_data[2] == 0:
            gr = cv2.cvtColor(self.frame2, cv2.COLOR_BGR2GRAY)
            self.frame2_thr = cv2.threshold(gr, 255 - thr_sl_val, 255, cv2.THRESH_BINARY)[1]
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
                blank = cv2.putText(blank, 'Name:{}'.format(name), (0, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Date:{}'.format(date), (0, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Mode:{}'.format(mode_str), (0, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Treshold:{}'.format(threshold), (0, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, temp, (0, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
                blank = cv2.putText(blank, 'Humidity:{}%'.format(preview_data[6]), (0, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
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
            self.zoom_button.text = "Zoom:\n{}x".format(self.zoomK)
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
                if parts[2] == '1':
                    print('Memorycard founded! path = ', parts[1], 'Total memory = ', parts[4])
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

class FilinApp(App):

    def build(self):
        # Create the screen manager
        sm = ScreenManager()
        sm.add_widget(InitScreen(name='init'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(ViewScreen(name='view'))

        return sm

    

if __name__ == '__main__':
    #global language, spot_color, capt_m, acc_period, temp_u, save_m
    cnfgprs.read('global.ini')
    language = int(cnfgprs['COMMON']['language'])
    spot_color[0] = float(cnfgprs['APPEARANCE']['spot_r'])
    spot_color[1] = float(cnfgprs['APPEARANCE']['spot_g'])
    spot_color[2] = float(cnfgprs['APPEARANCE']['spot_b'])
    acc_period = int(cnfgprs['APPEARANCE']['acc_period'])
    temp_u = int(cnfgprs['APPEARANCE']['temp_u'])
    capt_m = int(cnfgprs['MODES']['capture_m'])
    save_m = int(cnfgprs['MODES']['save_m'])
    FilinApp().run()

