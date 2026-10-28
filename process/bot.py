# Thread for bot actions

from gui import window
import time
import threading
from data import config, values, profiles
from process import behaviours, executor, kills
from tools import keyboard

potion_cooldown = config.potion_cooldown  # Seconds before the same key can be pressed again, shared when HP and MP use the same key
potion_confirm_reads = config.potion_confirm_reads  # Consecutive fresh low readings needed, so a single misread doesn't use a potion


class BotThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False

        self.profile = None  # Loaded from profiles/ by update_profile
        self.behaviour = None
        self.executor = None
        self.profile_request = None  # (name, version) last loaded or attempted

        self.potion_read_id = None  # Last HP/MP reading auto potion acted on
        self.potion_low_reads = {"HP": 0, "MP": 0}
        self.potion_key_time = {}  # time.time() each key was last pressed


    def run(self):
        while window.instance is not None:
            self.clear_values()
            self.auto_potion()  # Runs even when botting is off
            self.update_profile()
            if self.is_running is False:
                if self.executor is not None:
                    self.executor.stop_moving()  # Don't leave an arrow key held down
                time.sleep(0.2)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.001)  # Adjustable



    def calculate(self):
        if values.window_active is False or self.behaviour is None:
            return
        facing = {keyboard.VK_LEFT: "left", keyboard.VK_RIGHT: "right"}.get(self.executor.facing)
        situation = behaviours.Situation.from_values(time.time(), self.executor.attack_last_used, facing)
        action = self.behaviour.decide(situation)
        values.debug_action = action.label
        self.executor.run(action)
        if action.attack is not None and values.debug_mob is not None:  # For EXP Kill Check: the mob a kill right after this is of
            kills.instance.attacked(values.debug_mob, self.executor.attack_last_used[action.attack.name])
        if values.looting_active:  # spam loot
            self.executor.loot()


    def update_profile(self):  # Loads the profile picked in the Bot panel; a broken one is reported and the old one kept
        request = (values.bot_profile, values.bot_profile_version)
        if request == self.profile_request:
            return
        self.profile_request = request
        try:
            profile = profiles.load(values.bot_profile)
        except profiles.ProfileError as e:
            values.bot_profile_error = str(e)
            print("Bot profile:", e)
            return
        values.bot_profile_error = None
        if self.executor is not None:
            self.executor.stop_moving()
        self.profile = profile
        values.nav_jump_height = profile.platform_height  # Used by navigation to decide which platforms are in reach
        values.nav_clump_range = profile.clump_range  # Used by navigation to prefer bunched-up mobs
        self.behaviour = behaviours.for_profile(profile)
        self.executor = executor.Executor(profile)


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