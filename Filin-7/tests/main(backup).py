from kivy import require
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.progressbar import ProgressBar
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.config import Config
import timeit
from itertools import cycle

require("2.3.0")
debug = 1

if debug == 0:
    ##Config.set("graphics", "window_state", "maximized")
    Config.set("graphics", "fullscreen", 1)
    Config.set("graphics", "resizable", 0)
    Config.set("graphics", "show_cursor", 0)
else:
    Config.set("graphics", "fullscreen", 0)
    Config.set("graphics", "resizable", 0)
    Config.set("graphics", "show_cursor", 1)   

#Variables
menu_visibility = True
modes_visibility = False
thr_sl_visibility = False
gain_sl_visibility = False
thr_sl_val = 100
gain_sl_val = 10
click_types = cycle(["Shot", "Capture", "Expose"])
DOUBLE_TAP_TIME = 0.2   # Change time in seconds
LONG_PRESSED_TIME = 0.3  # Change time in seconds


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
    def showhide(self):
        global menu_visibility
        if menu_visibility:  
            anim = Animation(pos_hint = {"right": 2}, d = 0.5, t = "in_out_sine")
            anim2 = Animation(pos_hint = {"right": 1}, d = 0.5, t = "in_out_sine")
            anim.start(self.mode_button)
            anim.start(self.thr_button)
            anim.start(self.gain_button)
            anim.start(self.shot_button)
            anim.start(self.settings_button)
            self.shb.text = "<"
            anim2.start(self.shb)
            menu_visibility = False
        else:
            anim = Animation(pos_hint = {"right": 1}, d = 0.5, t = "in_out_sine")
            anim2 = Animation(pos_hint = {"right": 0.89}, d = 0.5, t = "in_out_sine")
            anim.start(self.mode_button)
            anim.start(self.thr_button)
            anim.start(self.gain_button)
            anim.start(self.shot_button)
            anim.start(self.settings_button)
            self.shb.text = ">"
            anim2.start(self.shb)
            menu_visibility = True
    

    def showmodes(self):
        global modes_visibility
        if modes_visibility == False:
            self.hide_all_subwidgets()
            anim1 = Animation(pos_hint = {"right": 0.74, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim2 = Animation(pos_hint = {"right": 0.82, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim3 = Animation(pos_hint = {"right": 0.9, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim1.start(self.mxmd)
            anim2.start(self.uvmd)
            anim3.start(self.vsmd)
            modes_visibility = True
        else:
            anim = Animation(pos_hint = {"right": 1.2, "top": 0.95}, d = 0.5, t = "in_out_sine")
            anim.start(self.mxmd)
            anim.start(self.uvmd)
            anim.start(self.vsmd)
            modes_visibility = False

    def acceptmodes(self, mode):
        global modes_visibility
        anim = Animation(pos_hint = {"right": 1.2, "top": 0.95}, d = 0.5, t = "in_out_sine")
        modes = ["Mix", "UV", "VIS"]
        self.mode_button.text = "Mode:\n{}".format(modes[mode])
        if mode == 0:
            self.thr_button.disabled = False
            self.gain_button.disabled = False
        elif mode == 1:
            self.thr_button.disabled = True
            self.gain_button.disabled = False
        elif mode == 2:
            self.thr_button.disabled = True
            self.gain_button.disabled = True
        anim.start(self.mxmd)
        anim.start(self.uvmd)
        anim.start(self.vsmd)
        modes_visibility = False
        print(mode)

    def showslider(self, slider):
        if debug == 1:
            print("showslider({}) event".format(slider))
        global thr_sl_visibility, gain_sl_visibility
        
        anim_show = Animation(pos_hint = {"right": 0.88, "top": 0.98}, d = 0.5, t = "in_out_sine")
        anim_hide = Animation(pos_hint = {"right": 1.8, "top": 0.98}, d = 0.5, t = "in_out_sine")
        if slider == 0:
            if thr_sl_visibility == False:
                self.hide_all_subwidgets()
                anim_show.start(self.thr_slider)
                thr_sl_visibility = True
                self.thr_slider.disabled = False
            else:
                anim_hide.start(self.thr_slider)
                thr_sl_visibility = False
                self.thr_slider.disabled = True
        elif slider == 1:
            if gain_sl_visibility == False:
                self.hide_all_subwidgets()
                anim_show.start(self.gain_slider)
                gain_sl_visibility = True
                self.gain_slider.disabled = False  
            else:
                anim_hide.start(self.gain_slider)
                gain_sl_visibility = False
                self.gain_slider.disabled = True
        pass

    def update_slider(self, slider):
        global thr_sl_val,  gain_sl_val
        if slider == 0:
            thr_sl_val = self.thr_slider.value
            self.thr_button.text = "Threshold:\n{}".format(int(thr_sl_val))
        elif slider == 1:
            gain_sl_val = self.gain_slider.value
            self.gain_button.text = "Gain:\n{}".format(int(gain_sl_val))

    def hide_all_subwidgets(self):
        global modes_visibility, thr_sl_visibility, gain_sl_visibility
        anim = Animation(pos_hint = {"right": 1.2, "top": 0.95}, d = 0.5, t = "in_out_sine")
        anim.start(self.mxmd)
        anim.start(self.uvmd)
        anim.start(self.vsmd)
        anim = Animation(pos_hint = {"right": 1.2, "top": 0.98}, d = 0.5, t = "in_out_sine")
        anim.start(self.thr_slider)
        anim.start(self.gain_slider)
        modes_visibility = False
        thr_sl_visibility = False
        gain_sl_visibility = False

    def shotclicked(self, click_type):
        if click_type == 0:
            print("Short clicked")
        elif click_type:
            self.shot_button.text = next(click_types)

            print("Long pressed")

class SettingsScreen(Screen):
    pass

class FilinApp(App):

    def build(self):
        # Create the screen manager
        sm = ScreenManager()
        sm.add_widget(InitScreen(name='init'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))

        return sm

class MultiExpressionButton(Button):

    def __init__(self, **kwargs):
        super(MultiExpressionButton, self).__init__(**kwargs)
        self.start = 0
        self.single_hit = 0
        self.press_state = False
        self.register_event_type('on_single_press')
        self.register_event_type('on_double_press')
        self.register_event_type('on_long_press')

    def on_touch_down(self, touch):
        if self.collide_point(touch.x, touch.y):
            self.start = timeit.default_timer()
            if touch.is_double_tap:
                self.press_state = True
                self.single_hit.cancel()
                self.dispatch('on_double_press')
        else:
            return super(MultiExpressionButton, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.press_state is False:
            if self.collide_point(touch.x, touch.y):
                stop = timeit.default_timer()
                awaited = stop - self.start

                def not_double(time):
                    nonlocal awaited
                    if awaited > LONG_PRESSED_TIME:
                        self.dispatch('on_long_press')
                    else:
                        self.dispatch('on_single_press')

                self.single_hit = Clock.schedule_once(not_double, DOUBLE_TAP_TIME)
            else:
                return super(MultiExpressionButton, self).on_touch_down(touch)
        else:
            self.press_state = False

    def on_single_press(self):
        pass

    def on_double_press(self):
        pass

    def on_long_press(self):
        pass







if __name__ == '__main__':
    FilinApp().run()
