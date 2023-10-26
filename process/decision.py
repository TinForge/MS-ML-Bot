from gui import window
import time
import threading
from tools import values
from process import data
from tools import key
from random import randrange
import keyboard


class DecisionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor

        global instance
        instance = self

        self.is_running = False
        self.key = key.VK_MENU


    def run(self):
        while window.instance is not None:
            event = keyboard.read_event()
            if event.event_type == keyboard.KEY_DOWN and event.name == "`":
                print("Toggling Decision Process")
                self.is_running = not self.is_running

            if self.is_running is False:
                time.sleep(0.01)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.01)  # Adjustable


    def calculate(self):
        if values.detected_instances is None:
            return

        instances = values.detected_instances

        player: data.Rect = data.find_rect_by_class(instances, "Player")
        monster: data.Rect = None

        values.debug_player = None
        values.debug_monster = None

        mob_instances = data.find_mob_instances(instances)

        if player is not None:
            values.debug_player = player
            mob_instances = data.filter_mobs_by_height(mob_instances, player, 140)  # Adjustable height threshold
            monster = data.find_closest_mob(mob_instances, player)
            # Determine if use mob skill
            # Determine if use power skill
        if monster is not None:
            values.debug_monster = monster

        # --------------------------------

        if player is not None and monster is not None and values.window_active is True:
            x_distance = monster.center_x - player.center_x
            y_distance = monster.center_y - player.center_y

            action = "nothing"
            direction = key.VK_MENU

            if x_distance < 0:
                action = "left"
                direction = key.VK_LEFT
            elif x_distance > 0:
                action = "right"
                direction = key.VK_RIGHT


            if abs(x_distance) > 150:  # Too far
                action = "move closer"
                self.move(direction)

            elif abs(x_distance) > 120:  # Within move jump attack range
                if y_distance > -25:  # Tall enough to hit
                    action = "move jump attack"
                    self.move_jump_attack(direction)
                else:
                    action = "move closer"
                    self.move(direction)

            elif abs(x_distance) < 120:  # Within attack range
                if y_distance > 75:  # Tall hit
                    action = "jump attack"
                    self.jump_attack(direction)
                else:  # Regular hit
                    action = "attack"
                    self.attack(direction)

            elif abs(x_distance) < 50:  # Too close
                action = "move farther"
                self.move(key.VK_RIGHT if direction == key.VK_LEFT else key.VK_LEFT)


            # if action == "left" and self.key is not keyboard.VK_LEFT:
            #     keyboard.ReleaseKey(self.key)
            #     self.key = keyboard.VK_LEFT
            #     keyboard.PressKey(self.key)

            # elif action == "right" and self.key is not keyboard.VK_RIGHT:
            #     keyboard.ReleaseKey(self.key)
            #     self.key = keyboard.VK_RIGHT
            #     keyboard.PressKey(self.key)

            # elif action == "attack":
            #     keyboard.ReleaseKey(self.key)
            #     self.key = keyboard.VK_CONTROL
            #     time.sleep(0.1)
            #     keyboard.PressKey(self.key)

            # elif action == "nothing":
            #     keyboard.ReleaseKey(self.key)
            #     self.key = keyboard.VK_MENU


            values.debug_action = action
            values.debug_distance = x_distance



    def move(self, direction):
        key.PressKey(direction)
        time.sleep(0.25)
        key.ReleaseKey(direction)

    def move_jump(self, direction):
        key.PressKey(direction)
        key.PressKey(key.VK_MENU)
        time.sleep(0.25)
        key.ReleaseKey(key.VK_MENU)
        key.ReleaseKey(direction)

    def move_jump_attack(self, direction):
        key.PressKey(direction)
        key.PressKey(key.VK_MENU)
        time.sleep(0.25)
        key.ReleaseKey(key.VK_MENU)
        key.ReleaseKey(direction)
        key.PressKey(key.VK_CONTROL)
        time.sleep(0.01)
        key.ReleaseKey(key.VK_CONTROL)

    def attack(self, direction):
        key.PressKey(direction)
        time.sleep(0.01)
        key.ReleaseKey(direction)

        key.PressKey(key.VK_CONTROL)
        time.sleep(0.01)
        key.ReleaseKey(key.VK_CONTROL)

    def jump_attack(self, direction):
        key.PressKey(key.VK_MENU)
        time.sleep(0.25)
        key.ReleaseKey(key.VK_MENU)

        key.PressKey(direction)
        time.sleep(0.01)
        key.ReleaseKey(direction)

        key.PressKey(key.VK_CONTROL)
        time.sleep(0.01)
        key.ReleaseKey(key.VK_CONTROL)


instance: DecisionThread = None
