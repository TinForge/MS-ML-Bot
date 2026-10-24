# Thread for bot actions

from gui import window
import time
import random
import threading
from data import values, profiles
from tools import keyboard

potion_cooldown = 3.0  # Seconds before the same key can be pressed again, shared when HP and MP use the same key
potion_confirm_reads = 2  # Consecutive fresh low readings needed, so a single misread doesn't use a potion


class BotThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False

        self.profile = profiles.WarriorLong()
        # self.profile = profiles.WarriorShort()

        self.old_direction = None

        self.potion_read_id = None  # Last HP/MP reading auto potion acted on
        self.potion_low_reads = {"HP": 0, "MP": 0}
        self.potion_key_time = {}  # time.time() each key was last pressed


    def run(self):
        while window.instance is not None:
            self.clear_values()
            self.auto_potion()  # Runs even when botting is off
            if self.is_running is False:
                time.sleep(0.2)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.001)  # Adjustable



    def calculate(self):
        if values.window_active is False:
            return

        x_distance = values.debug_x_distance
        y_distance = values.debug_y_distance
        direction = values.debug_direction


        if values.debug_state == "Attack":
            if values.debug_mob is None:
                return
            
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


        elif values.debug_state == "Navigate":
            if values.debug_path is None:
                return
            
            # if too far away
            if abs(x_distance) > 350:
                values.debug_action = "move closer"
                self.dash(direction)
                self.move(direction)

            # if far away
            elif abs(x_distance) > self.profile.platform_range:
                values.debug_action = "move closer"
                self.move(direction)

            # if too close
            elif abs(x_distance) == 0 and (y_distance < self.profile.platform_height):
                values.debug_action = "jump"
                self.move(None)
                self.jump(up=values.debug_on_ladder)

            # if within range
            elif abs(x_distance) < self.profile.platform_range and (y_distance < self.profile.platform_height):
                values.debug_action = "moving jump"
                self.move(None)
                self.move_jump(direction, up=values.debug_on_ladder)

        elif values.debug_state == "Search":
            self.up()
            if values.randomizer_active:
                values.debug_action = "random move"
                self.random_move()
                
        # spam loot
        if values.looting_active:
            self.loot()


    def clear_values(self):
        values.debug_action = "nothing"


    def auto_potion(self):
        read_id = values.stats_read_id
        if read_id == self.potion_read_id:  # Only act on fresh readings, never on a stale or frozen value
            return
        self.potion_read_id = read_id
        if values.potion_active is False or values.window_active is False:  # Never send keys to another window
            self.potion_low_reads = {"HP": 0, "MP": 0}
            return
        self.use_potion("HP", values.player_hp, values.hp_potion_threshold, values.hp_potion_key)
        self.use_potion("MP", values.player_mp, values.mp_potion_threshold, values.mp_potion_key)

    def use_potion(self, stat, value, threshold, key_name):  # Presses the key once the current value is confirmed at or below the threshold
        if value is None or value[0] > value[1] or threshold <= 0 or value[0] > threshold:  # Unknown, implausible or fine
            self.potion_low_reads[stat] = 0
            return
        self.potion_low_reads[stat] += 1
        if self.potion_low_reads[stat] < potion_confirm_reads:
            return
        if time.time() - self.potion_key_time.get(key_name, 0) < potion_cooldown:
            return
        self.potion_low_reads[stat] = 0  # Readings from before this potion never count towards the next
        self.potion_key_time[key_name] = time.time()
        values.last_potion_time[stat] = time.time()
        key = keyboard.KEY_NAMES[key_name]
        keyboard.PressKey(key)
        time.sleep(0.05)
        keyboard.ReleaseKey(key)


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


    def up(self):
        keyboard.PressKey(keyboard.VK_UP)
        time.sleep(1)
        keyboard.ReleaseKey(keyboard.VK_UP)


    def jump(self, up=False):
        keyboard.PressKey(keyboard.VK_MENU)
        time.sleep(0.25)
        if up:
            keyboard.PressKey(keyboard.VK_UP)
        keyboard.ReleaseKey(keyboard.VK_MENU)
        time.sleep(0.25)
        if up:
            time.sleep(1)
            keyboard.ReleaseKey(keyboard.VK_UP)

    def random_jump(self, chance):
        i = random.randint(1, chance)
        if i == chance:
            keyboard.PressKey(keyboard.VK_MENU)
            time.sleep(0.01)
            keyboard.ReleaseKey(keyboard.VK_MENU)

    def move_jump(self, direction, up=False):
        keyboard.PressKey(direction)
        time.sleep(0.15)
        keyboard.PressKey(keyboard.VK_MENU)
        if up:
            keyboard.PressKey(keyboard.VK_UP)
        time.sleep(0.25)
        keyboard.ReleaseKey(keyboard.VK_MENU)
        keyboard.ReleaseKey(direction)
        time.sleep(0.4)
        if up:
            time.sleep(1)
            keyboard.ReleaseKey(keyboard.VK_UP)

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