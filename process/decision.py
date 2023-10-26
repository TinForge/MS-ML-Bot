from gui import window
import time
import threading
from tools import values
from process import data
from tools import keyboard


class DecisionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor

        global instance
        instance = self

        self.is_running = False


    def run(self):
        while window.instance is not None:
            if self.is_running is False:
                time.sleep(0.01)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.01)  # Adjustable


    def calculate(self):
        detections = values.detected_models
        player: data.Rect = data.find_rect_by_class(detections, "Player")
        monster: data.Rect = None

        values.debug_player = None
        values.debug_monster = None

        if player is not None:
            values.debug_player = player
            monster = data.find_closest_monster(detections, player)
        if monster is not None:
            values.debug_monster = monster

        if player is not None and monster is not None and values.window_active is True:
            x_distance = monster.center_x - player.center_x
            y_distance = monster.center_y - player.center_y

            direction = "nothing"

            if x_distance < 0:
                direction = "left"
                keyboard.PressKey(keyboard.VK_LEFT)
                time.sleep(0.2)
                keyboard.ReleaseKey(keyboard.VK_LEFT)
            elif x_distance > 0:
                direction = "right"
                keyboard.PressKey(keyboard.VK_RIGHT)
                time.sleep(0.2)
                keyboard.ReleaseKey(keyboard.VK_RIGHT)
            if abs(x_distance) < 120:
                direction = "attack"
                keyboard.PressKey(keyboard.VK_CONTROL)
                time.sleep(0.2)
                keyboard.ReleaseKey(keyboard.VK_CONTROL)

            values.debug_action = direction
            values.debug_distance = x_distance




instance: DecisionThread = None
