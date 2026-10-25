# Turns behaviour actions into key presses, using the keys bound in the bot profile

import random
import time

from data.profiles import Profile
from tools import keyboard

DIRECTIONS = {"left": keyboard.VK_LEFT, "right": keyboard.VK_RIGHT}


class Executor:
    def __init__(self, profile: Profile):
        self.profile = profile
        self.held_direction = None  # Arrow key currently held for walking
        self.attack_last_used = {}  # Attack name: time.time() it was last used

    def key(self, name):  # A key bound in the profile, e.g. "jump"
        return keyboard.BIND_NAMES[self.profile.keys[name]]

    def run(self, action):
        direction = DIRECTIONS.get(action.direction)
        kind = action.kind
        if kind == "attack":
            self.move(None)
            self.attack(direction, action.attack)
        elif kind == "jump_attack":
            self.move(None)
            self.jump_attack(direction, action.attack)
        elif kind == "move":
            self.move(direction)
            if action.random_jump:
                self.random_jump(2)
        elif kind == "mobility":
            self.use_mobility(direction, action.mobility)
            self.move(direction)
            if action.random_jump:
                self.random_jump(2)
        elif kind == "stop":
            self.move(None)
        elif kind == "jump":
            self.move(None)
            self.jump(up=action.up)
        elif kind == "move_jump":
            self.move(None)
            self.move_jump(direction, up=action.up)
        elif kind == "drop":
            self.move(None)
            self.drop()
        elif kind == "search":
            self.up()
            if action.random_move:
                self.random_move()
        # wait: nothing to do

    def stop_moving(self):  # Releases a held arrow key, e.g. when botting is turned off
        self.move(None)

    # -----------------------------------------------

    def tap(self, vk, hold):
        keyboard.PressKey(vk)
        time.sleep(hold)
        keyboard.ReleaseKey(vk)

    def attack(self, direction, attack):
        self.tap(direction, 0.05)  # Face the mob
        self.tap(keyboard.BIND_NAMES[attack.key], 0.01)
        self.attack_last_used[attack.name] = time.time()

    def jump_attack(self, direction, attack):
        self.tap(self.key("jump"), 0.4)
        self.tap(direction, 0.01)
        self.tap(keyboard.BIND_NAMES[attack.key], 0.01)
        self.attack_last_used[attack.name] = time.time()

    def use_mobility(self, direction, mobility):
        if mobility.type == "dash":
            self.tap(direction, 0.05)
            self.tap(keyboard.BIND_NAMES[mobility.key], 0.05)
        elif mobility.type == "teleport":
            keyboard.PressKey(direction)
            self.tap(keyboard.BIND_NAMES[mobility.key], 0.2)
            keyboard.ReleaseKey(direction)
        elif mobility.type == "flash_jump":  # Jump, then jump again mid-air while holding the direction
            keyboard.PressKey(direction)
            self.tap(self.key("jump"), 0.1)
            time.sleep(0.1)
            self.tap(self.key("jump"), 0.05)
            keyboard.ReleaseKey(direction)

    def move(self, direction):
        if direction is None and self.held_direction is not None:  # stop moving
            keyboard.ReleaseKey(self.held_direction)
        elif direction != self.held_direction and self.held_direction is not None:  # change direction
            keyboard.ReleaseKey(self.held_direction)
            keyboard.PressKey(direction)
            time.sleep(0.1)
        elif self.held_direction is not None:  # continue
            keyboard.PressKey(self.held_direction)
            time.sleep(0.1)
        self.held_direction = direction

    def up(self):
        self.tap(keyboard.VK_UP, 1)

    def jump(self, up=False):
        keyboard.PressKey(self.key("jump"))
        time.sleep(0.25)
        if up:
            keyboard.PressKey(keyboard.VK_UP)
        keyboard.ReleaseKey(self.key("jump"))
        time.sleep(0.25)
        if up:
            time.sleep(1)
            keyboard.ReleaseKey(keyboard.VK_UP)

    def drop(self):  # Down + jump falls through the platform
        keyboard.PressKey(keyboard.VK_DOWN)
        time.sleep(0.1)
        self.tap(self.key("jump"), 0.1)
        time.sleep(0.2)
        keyboard.ReleaseKey(keyboard.VK_DOWN)

    def random_jump(self, chance):
        if random.randint(1, chance) == chance:
            self.tap(self.key("jump"), 0.01)

    def move_jump(self, direction, up=False):
        keyboard.PressKey(direction)
        time.sleep(0.15)
        keyboard.PressKey(self.key("jump"))
        if up:
            keyboard.PressKey(keyboard.VK_UP)
        time.sleep(0.25)
        keyboard.ReleaseKey(self.key("jump"))
        keyboard.ReleaseKey(direction)
        time.sleep(0.4)
        if up:
            time.sleep(1)
            keyboard.ReleaseKey(keyboard.VK_UP)

    def loot(self):
        self.tap(self.key("loot"), 0.01)

    def random_move(self):
        self.tap(random.choice((keyboard.VK_LEFT, keyboard.VK_RIGHT)), 0.2)
