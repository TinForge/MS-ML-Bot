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

        self.profile = profiles.WarriorLong()
        # self.profile = profiles.WarriorShort()

        self.old_direction = None


    def run(self):
        while window.instance is not None:
            self.clear_values()
            if self.is_running is False:
                time.sleep(0.2)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.001)  # Adjustable


    """

    """


    def calculate(self):
        if values.window_active is False:
            return

        x_distance = values.debug_x_distance
        y_distance = values.debug_y_distance
        direction = values.debug_direction
        player = values.debug_player
        mob = values.debug_mob

        if mob is None:
            values.debug_state = "Navigate"
        else: 
            values.debug_state = "Attack"


        # if has target
        if player is not None and mob is not None:

            # if too far away
            if abs(x_distance) > 350:
                values.debug_action = "move closer"
                self.dash(direction)
                self.move(direction)
                if values.randomizer_active:
                    self.random_jump(2)

            # if far away
            elif abs(x_distance) > self.profile.max_range:
                values.debug_action = "move closer"
                self.move(direction)

            # if within range
            elif abs(x_distance) < self.profile.max_range:
                self.move(None)

                if y_distance > self.profile.min_height and y_distance < self.profile.max_height:
                    values.debug_action = "attack"
                    self.attack(direction)
                elif y_distance > self.profile.max_height and y_distance < self.profile.max_height + 75:
                    values.debug_action = "jump attack"
                    self.jump_attack(direction)
                elif y_distance < self.profile.min_height:
                    values.debug_action = "move closer"
                    # self.move(direction)
                elif y_distance < -150:
                    values.debug_action = "floor drop"

            # if too close
            elif abs(x_distance) < self.profile.min_range:
                values.debug_action = "move away"
                self.move(keyboard.VK_RIGHT if direction == keyboard.VK_LEFT else keyboard.VK_LEFT)

            # spam loot
            if values.looting_active:
                self.loot()

        # if no target
        elif player is not None and mob is None:
            if values.randomizer_active:
                values.debug_action = "random move"
                self.random_move()


    def clear_values(self):
        values.debug_action = "nothing"


    # -----------------------------------------------


    def dash(self, direction):
        keyboard.PressKey(direction)
        time.sleep(0.05)
        keyboard.ReleaseKey(direction)

        keyboard.PressKey(keyboard.VK_SHIFT)
        time.sleep(0.05)
        keyboard.ReleaseKey(keyboard.VK_SHIFT)


    def attack(self, direction):
        keyboard.PressKey(direction)
        time.sleep(0.05)
        keyboard.ReleaseKey(direction)

        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.01)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def move(self, direction):
        if direction is None and self.old_direction is not None:  # stop moving
            keyboard.ReleaseKey(self.old_direction)
        elif direction is not self.old_direction and self.old_direction is not None:  # move
            keyboard.ReleaseKey(self.old_direction)
            keyboard.PressKey(direction)
            time.sleep(0.1)
        elif self.old_direction is not None:  # continue
            keyboard.PressKey(self.old_direction)
            time.sleep(0.1)

        self.old_direction = direction


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



"""
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

        if self.i < (5 / 0.1):  # total timer
            self.i += 1
            self.attack()
            if self.i % 60 == 0:  # occasional move
                self.move_right()
        else:
            self.i = 0
            self.teleport(keyboard.VK_LEFT)
            self.teleport(keyboard.VK_LEFT)
            self.teleport(keyboard.VK_LEFT)
            self.move_right()

    # -----------------------------------------------


    def attack(self):
        keyboard.PressKey(keyboard.VK_CONTROL)
        time.sleep(0.1)
        keyboard.ReleaseKey(keyboard.VK_CONTROL)

    def move_left(self):
        keyboard.PressKey(keyboard.VK_LEFT)
        time.sleep(0.15)
        keyboard.ReleaseKey(keyboard.VK_LEFT)

    def move_right(self):
        keyboard.PressKey(keyboard.VK_RIGHT)
        time.sleep(0.15)
        keyboard.ReleaseKey(keyboard.VK_RIGHT)

    def pot(self):
        keyboard.PressKey(keyboard.VK_DELETE)
        time.sleep(0.15)
        keyboard.ReleaseKey(keyboard.VK_DELETE)

    def teleport(self, direction):
        time.sleep(0.1)
        keyboard.PressKey(direction)
        keyboard.PressKey(keyboard.VK_SHIFT)
        time.sleep(0.2)
        keyboard.ReleaseKey(keyboard.VK_SHIFT)
        keyboard.ReleaseKey(direction)


instance: MacroThread = None
"""