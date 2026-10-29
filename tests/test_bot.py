# Tests for the bot thread's tick: auto potion, profile loading and attacking, without sending keys

import os
import time
import unittest
from unittest import mock

from data import profiles, values
from data.rects import Rect
from process import bot
from tools import keyboard


class BotTickTests(unittest.TestCase):
    def setUp(self):
        saved = {name: getattr(values, name) for name in ("bot_profile", "window_active", "looting_active", "potion_active", "debug_state",
                                                           "debug_mob", "debug_player", "debug_x_distance", "debug_y_distance", "debug_crowd")}
        self.addCleanup(lambda: [setattr(values, name, value) for name, value in saved.items()])
        fixtures = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "profiles")  # Not your edited profiles
        patches = [mock.patch.object(keyboard, "PressKey"), mock.patch.object(keyboard, "ReleaseKey"), mock.patch("time.sleep"),
                   mock.patch.object(profiles, "folder", fixtures)]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_one_tick_with_an_attack(self):  # Every step of BotThread.run, so a method lost from the class fails here
        b = bot.BotThread()
        values.bot_profile, values.window_active, values.looting_active, values.potion_active = "swordsman", True, False, False
        b.clear_values()
        b.auto_potion()
        b.update_profile()
        self.assertIsNotNone(b.behaviour)
        values.debug_state, values.debug_x_distance, values.debug_y_distance, values.debug_crowd = "Attack", 50, 0, [(50, 0), (80, 0)]
        values.debug_mob = Rect("Mob", "red", 525, 280, 575, 320, 0.9, int(time.time() * 1000))
        values.debug_player = Rect("Player", "blue", 450, 254, 500, 320, 1)
        b.calculate()
        self.assertEqual(values.debug_action, "attack: Mobbing attack (2 in mobbing reach)")


if __name__ == "__main__":
    unittest.main()
