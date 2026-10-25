# Tests for bot profiles, behaviours and the executor. Run from the repository root:
#   .venv\Scripts\python.exe -m unittest discover -s tests -t .

import unittest
from unittest import mock

from data import profiles
from process import behaviours, executor
from process.behaviours import Situation
from tools import keyboard


def decide(profile_name, **situation):
    profile = profiles.load(profile_name)
    return behaviours.for_profile(profile).decide(Situation(**situation))


class ProfileTests(unittest.TestCase):
    def test_shipped_profiles_load(self):
        names = profiles.available()
        self.assertTrue({"spearman", "swordsman", "hunter", "assassin"} <= set(names))
        for name in names:
            profiles.load(name)

    def test_spearman_matches_old_warrior_long(self):
        p = profiles.load("spearman")
        self.assertEqual((p.min_range, p.max_range), (70, 150))
        self.assertEqual(p.attacks[0].range_y, (-30, 75))
        self.assertEqual((p.platform_range, p.platform_height), (50, 100))

    def check_invalid(self, data, message):
        with self.assertRaises(profiles.ProfileError) as e:
            profiles.from_dict("test", data)
        self.assertIn(message, str(e.exception))

    def test_invalid_profiles_are_reported(self):
        attack = {"key": "Ctrl", "range_x": [0, 100], "range_y": [-10, 10]}
        self.check_invalid({"attacks": [dict(attack, key="Ctlr")]}, "not a known key")
        self.check_invalid({"attacks": [dict(attack, range_x=[100, 0])]}, "range_x must be [min, max]")
        self.check_invalid({"behaviour": "summoner", "attacks": [attack]}, "behaviour must be one of")
        self.check_invalid({}, "at least one [[attacks]]")
        self.check_invalid({"attacks": [attack], "mobility": [{"type": "dash"}]}, "needs a key")
        self.check_invalid({"attacks": [attack], "keys": {"jump": "Altt"}}, "not a known key")
        profiles.from_dict("test", {"attacks": [attack], "mobility": [{"type": "flash_jump"}]})  # Uses the jump key

    def test_missing_profile(self):
        with self.assertRaises(profiles.ProfileError):
            profiles.load("does_not_exist")

    def test_attack_priority_and_cooldown(self):
        p = profiles.load("hunter")
        self.assertEqual(p.attack_for(200, 0).name, "Arrow Bomb")  # Listed first
        self.assertEqual(p.attack_for(200, 0, {"Arrow Bomb": 10.0}, now=11.0).name, "Basic shot")  # On cooldown
        self.assertEqual(p.attack_for(200, 0, {"Arrow Bomb": 10.0}, now=12.0).name, "Arrow Bomb")  # Ready again
        self.assertEqual(p.attack_for(390, 0).name, "Basic shot")  # Only it reaches that far

    def test_mobility_picks_longest_applicable(self):
        p = profiles.from_dict("test", {"attacks": [{"key": "Ctrl", "range_x": [0, 100], "range_y": [0, 0]}],
                                        "mobility": [{"type": "dash", "key": "Shift", "min_distance": 300},
                                                     {"type": "teleport", "key": "X", "min_distance": 500}]})
        self.assertIsNone(p.mobility_for(200))
        self.assertEqual(p.mobility_for(400).type, "dash")
        self.assertEqual(p.mobility_for(600).type, "teleport")


class MeleeTests(unittest.TestCase):
    def test_far_mob_uses_dash(self):
        a = decide("spearman", state="Attack", dx=400, randomizer=True)
        self.assertEqual((a.kind, a.mobility.type, a.direction, a.random_jump), ("mobility", "dash", "right", True))

    def test_moves_closer(self):
        self.assertEqual((decide("spearman", state="Attack", dx=200).kind, decide("spearman", state="Attack", dx=-200).direction), ("move", "left"))

    def test_attacks_in_range(self):
        a = decide("spearman", state="Attack", dx=-100, dy=0)
        self.assertEqual((a.kind, a.direction, a.attack.name), ("attack", "left", "Basic attack"))

    def test_jump_attacks_mob_slightly_above(self):
        self.assertEqual(decide("spearman", state="Attack", dx=100, dy=100).kind, "jump_attack")
        self.assertEqual(decide("swordsman", state="Attack", dx=50, dy=50).kind, "jump_attack")

    def test_stops_when_mob_out_of_vertical_reach(self):
        self.assertEqual(decide("spearman", state="Attack", dx=100, dy=200).kind, "stop")

    def test_too_close_steps_back(self):  # Unreachable before: the in-range check ran first
        a = decide("spearman", state="Attack", dx=30, dy=0)
        self.assertEqual((a.kind, a.direction, a.label), ("move", "left", "move away"))


class RangedTests(unittest.TestCase):
    def test_backs_off_when_mob_close(self):
        a = decide("hunter", state="Attack", dx=100, dy=0)
        self.assertEqual((a.kind, a.direction, a.label), ("move", "left", "back off"))

    def test_ignores_close_mob_on_another_platform(self):
        self.assertEqual(decide("hunter", state="Attack", dx=100, dy=150).kind, "stop")

    def test_shoots_in_range(self):
        a = decide("hunter", state="Attack", dx=-250, dy=10)
        self.assertEqual((a.kind, a.direction, a.attack.name), ("attack", "left", "Arrow Bomb"))

    def test_never_jump_attacks(self):
        self.assertEqual(decide("hunter", state="Attack", dx=250, dy=60).kind, "stop")

    def test_walks_without_mobility(self):
        self.assertEqual(decide("hunter", state="Attack", dx=600).kind, "move")

    def test_flash_jump_closes_distance(self):
        a = decide("assassin", state="Attack", dx=-300)
        self.assertEqual((a.kind, a.mobility.type, a.direction), ("mobility", "flash_jump", "left"))


class SharedTests(unittest.TestCase):
    def test_navigation(self):
        self.assertEqual(decide("spearman", state="Navigate", dx=400).kind, "mobility")
        self.assertEqual(decide("spearman", state="Navigate", dx=-100).kind, "move")
        a = decide("spearman", state="Navigate", dx=0, dy=50, on_ladder=True)
        self.assertEqual((a.kind, a.up), ("jump", True))
        self.assertEqual(decide("spearman", state="Navigate", dx=30, dy=50).kind, "move_jump")
        self.assertEqual(decide("spearman", state="Navigate", dx=30, dy=150).kind, "wait")

    def test_navigation_same_for_every_style(self):
        for dx, dy in [(-100, 0), (0, 50), (30, 50), (30, 150)]:
            self.assertEqual(decide("spearman", state="Navigate", dx=dx, dy=dy).kind, decide("hunter", state="Navigate", dx=dx, dy=dy).kind)

    def test_search_and_idle(self):
        a = decide("hunter", state="Search", randomizer=True)
        self.assertEqual((a.kind, a.random_move), ("search", True))
        self.assertEqual(decide("hunter").kind, "wait")


class ExecutorTests(unittest.TestCase):
    def run_action(self, profile_name, action):
        presses = []
        e = executor.Executor(profiles.load(profile_name))
        with mock.patch.object(keyboard, "PressKey", lambda k: presses.append(k)), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: None), mock.patch("time.sleep"):
            e.run(action)
        return e, presses

    def test_attack_uses_profile_key_and_records_use(self):
        p = profiles.load("hunter")
        e, presses = self.run_action("hunter", behaviours.Action("attack", "right", attack=p.attacks[0]))
        self.assertEqual(presses, [keyboard.VK_RIGHT, keyboard.VK_SHIFT])  # Face right, then Arrow Bomb on Shift
        self.assertIn("Arrow Bomb", e.attack_last_used)

    def test_flash_jump_presses_jump_twice(self):
        p = profiles.load("assassin")
        e, presses = self.run_action("assassin", behaviours.Action("mobility", "left", mobility=p.mobility[0]))
        self.assertEqual(presses.count(keyboard.VK_MENU), 2)

    def test_stop_moving_releases_held_arrow(self):
        e = executor.Executor(profiles.load("spearman"))
        released = []
        with mock.patch.object(keyboard, "PressKey", lambda k: None), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: released.append(k)), mock.patch("time.sleep"):
            e.move(keyboard.VK_LEFT)
            e.stop_moving()
        self.assertEqual((released, e.held_direction), ([keyboard.VK_LEFT], None))


if __name__ == "__main__":
    unittest.main()
