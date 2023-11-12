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
        # self.profile = profiles.WarriorShort()
        self.profile = profiles.WarriorLong()


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

            if abs(x_distance) > 350:
                values.debug_action = "move closer"
                self.move(direction)
                self.random_jump(2)

            elif abs(x_distance) > self.profile.max_range:
                values.debug_action = "move closer"
                self.move(direction)

            elif abs(x_distance) < self.profile.max_range:
                if y_distance > self.profile.min_height and y_distance < self.profile.max_height:
                    values.debug_action = "attack"
                    self.attack(direction)
                elif y_distance > self.profile.max_height and y_distance < self.profile.max_height + 75:
                    values.debug_action = "jump attack"
                    self.jump_attack(direction)
                elif y_distance < self.profile.min_height:
                    values.debug_action = "move closer"
                    self.move(direction)
                elif y_distance < -150:
                    values.debug_action = "floor drop"

            elif abs(x_distance) < self.profile.min_range:
                values.debug_action = "move away"
                self.move(keyboard.VK_RIGHT if direction == keyboard.VK_LEFT else keyboard.VK_LEFT)

            self.loot()

        elif player is not None and mob is None:
            values.debug_action = "random move"
            self.random_move()


    def clear_values(self):
        values.debug_action = "nothing"


    # -----------------------------------------------


    def attack(self, direction):
        keyboard.PressKey(direction)
        time.sleep(0.05)
        keyboard.ReleaseKey(direction)

        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.01)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def move(self, direction):
        keyboard.PressKey(direction)
        time.sleep(0.2)
        keyboard.ReleaseKey(direction)

    def random_jump(self, chance):
        i = random.randint(1, chance)
        if i == chance:
            keyboard.PressKey(keyboard.VK_MENU)
            time.sleep(0.01)
            keyboard.ReleaseKey(keyboard.VK_MENU)

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
        time.sleep(0.4)
        keyboard.ReleaseKey(keyboard.VK_MENU)

        keyboard.PressKey(direction)
        time.sleep(0.01)
        keyboard.ReleaseKey(direction)

        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.01)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def loot(self):
        # i = random.randint(1, 4)
        # if i == 4:
        keyboard.PressKey(keyboard.VK_Z)
        # time.sleep(0.01)
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





class MacroThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.i = 0


    def run(self):
        while window.instance is not None:
            if self.is_running is False:
                time.sleep(0.1)  # Adjustable
            else:
                self.macro()
                time.sleep(0.01)  # Adjustable


    def macro(self):
        if values.window_active is False:
            return

        if self.i < (45 / 0.2):  # total timer
            self.i += 1
            self.attack()
            if self.i % 50 == 0:  # occasional move
                self.move()
        else:
            self.pot()  # heal and reset
            self.i = 0

    # -----------------------------------------------


    def attack(self):
        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.2)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def move(self):
        keyboard.PressKey(keyboard.VK_LEFT)
        time.sleep(0.15)
        keyboard.ReleaseKey(keyboard.VK_LEFT)

    def pot(self):
        keyboard.PressKey(keyboard.VK_DELETE)
        time.sleep(0.15)
        keyboard.ReleaseKey(keyboard.VK_DELETE)


instance: MacroThread = None