# Thread for bot actions

from gui import window
import time
import random
import threading
from data import values, profiles
from tools import keyboard


class BotThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.profile = profiles.WarriorShort()


    def run(self):
        while window.instance is not None:
            self.clear_values()
            if self.is_running is False:
                time.sleep(0.1)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.01)  # Adjustable


    def calculate(self):
        if values.window_active is False:
            return

        x_distance = values.debug_x_distance
        y_distance = values.debug_y_distance
        direction = values.debug_direction
        player = values.debug_player
        mob = values.debug_mob

        if player is not None and mob is not None:

            if abs(x_distance) > self.profile.max_range:
                values.debug_action = "move closer"
                self.move(direction)

            elif abs(x_distance) < self.profile.max_range:
                if y_distance > self.profile.min_height and y_distance < self.profile.max_height:
                    values.debug_action = "attack"
                    self.attack(direction)
                elif y_distance > self.profile.max_height and y_distance < self.profile.max_height + 50:
                    values.debug_action = "jump attack"
                    self.jump_attack(direction)

            elif abs(x_distance) < self.profile.min_range:
                values.debug_action = "move away"
                self.move(keyboard.VK_RIGHT if direction == keyboard.VK_LEFT else keyboard.VK_LEFT)

        elif player is not None and mob is None:
            values.debug_action = "random move"
            self.random_move()
            self.loot()


    def clear_values(self):
        values.debug_action = "nothing"


    # -----------------------------------------------


    def attack(self, direction):
        keyboard.PressKey(direction)
        time.sleep(0.01)
        keyboard.ReleaseKey(direction)

        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.01)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def move(self, direction):
        keyboard.PressKey(direction)
        time.sleep(0.3)
        keyboard.ReleaseKey(direction)

    def move_jump(self, direction):
        keyboard.PressKey(direction)
        keyboard.PressKey(keyboard.VK_MENU)
        time.sleep(0.25)
        keyboard.ReleaseKey(keyboard.VK_MENU)
        keyboard.ReleaseKey(direction)

    def move_jump_attack(self, direction):
        keyboard.PressKey(direction)
        keyboard.PressKey(keyboard.VK_MENU)
        time.sleep(0.6)
        keyboard.ReleaseKey(keyboard.VK_MENU)
        keyboard.ReleaseKey(direction)
        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.01)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def jump_attack(self, direction):
        keyboard.PressKey(keyboard.VK_MENU)
        time.sleep(0.6)
        keyboard.ReleaseKey(keyboard.VK_MENU)

        keyboard.PressKey(direction)
        time.sleep(0.01)
        keyboard.ReleaseKey(direction)

        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.01)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def loot(self):
        i = random.randint(1, 4)
        if i == 4:
            keyboard.PressKey(keyboard.VK_Z)
            time.sleep(0.01)
            keyboard.ReleaseKey(keyboard.VK_Z)

    def random_move(self):
        i = random.randint(1, 2)
        direction = keyboard.VK_LEFT if i == 1 else keyboard.VK_RIGHT
        keyboard.PressKey(direction)
        time.sleep(0.2)
        keyboard.ReleaseKey(direction)


instance: BotThread = None


# event = keyboard.read_event()
# if event.event_type == keyboard.KEY_DOWN and event.name == "`":
#     print("Toggling Decision Process")
#     self.is_running = not self.is_running