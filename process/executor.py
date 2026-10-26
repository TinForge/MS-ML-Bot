# Turns behaviour actions into key presses, using the keys bound in the bot profile

import random
import time

from data import config, values
from data.profiles import Profile
from tools import keyboard

DIRECTIONS = {"left": keyboard.VK_LEFT, "right": keyboard.VK_RIGHT}
loot_interval = 0.1  # Seconds between loot presses: pressed every bot tick, it reached ~75 a second and froze the game client
idle_sleep = 0.02  # Pause after an action that sends no keys (stop, wait), so the bot loop doesn't spin
walk_step = 0.05  # Seconds an arrow key is held per walking tick before the bot looks again; longer overshoots the mob
nudge_time = 0.04  # Seconds an arrow is tapped to shuffle a few pixels into place
nudge_settle = 0.08  # Seconds to wait after a nudge, so the next look sees where it ended up


class Executor:
    def __init__(self, profile: Profile):
        self.profile = profile
        self.held_direction = None  # Arrow key currently held for walking
        self.holding_up = False  # Up held for climbing a rope (or catching one while jumping)
        self.holding_jump = False  # Jump held while walking: the character hops along (Random Behaviour)
        self.facing = None  # Arrow key of the way the character last faced, None if unknown
        self.attack_last_used = {}  # Attack name: time.time() it was last used
        self.last_loot = 0  # time.time() the loot key was last pressed
        self.next_press = 0  # time.time() before which the next tap waits, like a person's fingers between taps

    def key(self, name):  # A key bound in the profile, e.g. "jump"
        return keyboard.BIND_NAMES[self.profile.keys[name]]

    def run(self, action):
        direction = DIRECTIONS.get(action.direction)
        kind = action.kind
        if kind != "climb" and not action.up:
            self.hold_up(False)
        if not (kind == "move" and action.jump):
            self.hold_jump(False)
        if kind == "climb":
            self.move(None)
            self.hold_up(True)
            self.pause(walk_step)
        elif kind == "attack":
            self.move(None)
            self.attack(direction, action.attack)
        elif kind == "jump_attack":
            self.move(None)
            self.jump_attack(direction, action.attack)
        elif kind == "nudge":
            self.move(None)
            self.press(direction, nudge_time)
            self.facing = direction
            time.sleep(nudge_settle)
        elif kind == "jump_off":
            self.move(None)
            self.jump_off(direction)
        elif kind == "move":
            self.move(direction)
            self.hold_jump(action.jump)
        elif kind == "mobility":
            self.use_mobility(direction, action.mobility)
            self.move(direction)
        elif kind == "stop":
            self.move(None)
            time.sleep(idle_sleep)
        elif kind == "jump":
            self.move(None)
            self.jump(up=action.up)
        elif kind == "move_jump":
            self.move(None)
            self.move_jump(direction, up=action.up)
        elif kind == "drop":
            self.move(None)
            self.drop()
        else:  # wait: nothing to do
            time.sleep(idle_sleep)

    def stop_moving(self):  # Releases a held arrow key (and Up and jump), e.g. when botting is turned off
        self.move(None)
        self.hold_up(False)
        self.hold_jump(False)

    def hold_jump(self, held):  # Holds or lets go of jump; held, the character jumps again each time it lands
        if held:
            keyboard.PressKey(self.key("jump"))
        elif self.holding_jump:
            keyboard.ReleaseKey(self.key("jump"))
        self.holding_jump = held

    def hold_up(self, held):  # Holds or lets go of Up; held, it's pressed again each time like a held key repeating
        if held:
            keyboard.PressKey(keyboard.VK_UP)
        elif self.holding_up:
            keyboard.ReleaseKey(keyboard.VK_UP)
        self.holding_up = held

    # -----------------------------------------------

    def press(self, vk, exact=0.01):  # One tap; returns when the key went down. With Human Key Presses on, held about as long as a
        # person holds a key and not sooner after the last than a person could; otherwise held exactly `exact` seconds, right away
        if not values.human_input:
            down = time.time()
            keyboard.PressKey(vk)
            time.sleep(exact)
            keyboard.ReleaseKey(vk)
            return down
        wait = self.next_press - time.time()
        if wait > 0:
            time.sleep(wait)
        down = time.time()
        keyboard.PressKey(vk)
        time.sleep(random.uniform(*config.press_time))
        keyboard.ReleaseKey(vk)
        self.next_press = time.time() + random.uniform(*config.press_gap)
        return down

    def pause(self, seconds):  # A deliberate hold or wait; varied a little like a person's with Human Key Presses on
        time.sleep(seconds * random.uniform(1 - config.hold_jitter, 1 + config.hold_jitter) if values.human_input else seconds)

    def tap(self, vk, hold):  # A key held for a set time (a jump, a climb), varied a little
        keyboard.PressKey(vk)
        self.pause(hold)
        keyboard.ReleaseKey(vk)

    def face(self, direction):  # Turns towards the mob only when needed: every tap of an arrow key also walks a step. None: as it is
        if direction is not None and direction != self.facing:
            self.press(direction, 0.05)
            self.facing = direction

    def attack(self, direction, attack):
        self.face(direction)
        self.attack_last_used[attack.name] = self.press(keyboard.BIND_NAMES[attack.key])  # From the key going down, for hit_time

    def jump_attack(self, direction, attack):
        self.tap(self.key("jump"), 0.4)
        self.face(direction)
        self.attack_last_used[attack.name] = self.press(keyboard.BIND_NAMES[attack.key])

    def use_mobility(self, direction, mobility):
        self.facing = direction
        if mobility.type == "dash":
            self.press(direction, 0.05)
            self.press(keyboard.BIND_NAMES[mobility.key], 0.05)
        elif mobility.type == "teleport":
            keyboard.PressKey(direction)
            self.tap(keyboard.BIND_NAMES[mobility.key], 0.2)
            keyboard.ReleaseKey(direction)
        elif mobility.type == "flash_jump":  # Jump, then jump again mid-air while holding the direction
            keyboard.PressKey(direction)
            self.tap(self.key("jump"), 0.1)
            self.pause(0.1)
            self.press(self.key("jump"), 0.05)
            keyboard.ReleaseKey(direction)

    def move(self, direction):
        if direction is None and self.held_direction is not None:  # stop moving
            keyboard.ReleaseKey(self.held_direction)
        elif direction != self.held_direction and self.held_direction is not None:  # change direction
            keyboard.ReleaseKey(self.held_direction)
            keyboard.PressKey(direction)
            self.pause(walk_step)
        elif self.held_direction is not None:  # continue
            keyboard.PressKey(self.held_direction)
            self.pause(walk_step)
        self.held_direction = direction
        if direction is not None:
            self.facing = direction

    def jump(self, up=False):  # up: holding Up from the start catches a rope overhead; it stays held for climbing on
        if up:
            self.hold_up(True)
        keyboard.PressKey(self.key("jump"))
        self.pause(0.25)
        keyboard.ReleaseKey(self.key("jump"))
        self.pause(0.25)

    def jump_off(self, direction):  # Off a rope: a direction and jump together leave it sideways
        keyboard.PressKey(direction)
        self.pause(0.05)
        self.press(self.key("jump"), 0.1)
        self.pause(0.2)
        keyboard.ReleaseKey(direction)
        self.facing = direction

    def drop(self):  # Down + jump falls through the platform
        keyboard.PressKey(keyboard.VK_DOWN)
        self.pause(0.1)
        self.tap(self.key("jump"), 0.1)
        self.pause(0.2)
        keyboard.ReleaseKey(keyboard.VK_DOWN)

    def move_jump(self, direction, up=False):
        self.facing = direction
        keyboard.PressKey(direction)
        self.pause(0.15)
        if up:
            self.hold_up(True)  # Stays held for climbing on, as with jump
        keyboard.PressKey(self.key("jump"))
        self.pause(0.25)
        keyboard.ReleaseKey(self.key("jump"))
        keyboard.ReleaseKey(direction)
        self.pause(0.4)

    def loot(self):
        now = time.time()
        if now - self.last_loot >= loot_interval:
            self.press(self.key("loot"))
            self.last_loot = now
