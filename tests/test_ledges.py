# Tests for keeping away from ledges while fighting, so a mob's hit doesn't knock the player off the platform

import unittest
from unittest import mock

from data import profiles, values
from process import behaviours, calculations
from process.behaviours import Situation, ledge_margin
from tests.test_behaviours import FIXTURES
from tests.test_route_planner import GROUND, LEDGE, TOP, RouterTests, planner
from tools.route_planner import RoutePlanner


def setUpModule():  # Fixed copies of the profiles, as in test_behaviours
    patcher = mock.patch.object(profiles, "folder", FIXTURES)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


class LedgeTests(unittest.TestCase):  # On test_route_planner's made-up map
    def test_ends_over_lower_ground_are_ledges(self):
        r = planner()
        self.assertEqual(r.ledges(LEDGE, 950), (50, 150))
        self.assertEqual(r.ledges(TOP, 700), (300, 100))

    def test_ends_with_nothing_below_are_not(self):  # Walls and the bottom of the map: nothing to fall onto
        self.assertEqual(planner().ledges(GROUND, 100), (None, None))

    def test_a_platform_recorded_in_pieces_counts_whole(self):
        r = RoutePlanner([[(0, 600), (1200, 600)], [(900, 520), (1000, 520)], [(1012, 521), (1100, 521)]], [], jump_height=100)
        self.assertEqual(r.ledges(1, 950), (50, 150))
        self.assertEqual(r.ledges(2, 1050), (150, 50))

    def test_a_step_down_is_not_a_ledge(self):  # A stair a few pixels lower: walked down, nothing to fall off
        r = RoutePlanner([[(0, 600), (500, 600)], [(510, 615), (900, 615)]], [], jump_height=100)
        self.assertEqual(r.ledges(0, 400), (None, None))


class OffLedgeTests(unittest.TestCase):
    def decide(self, dx, ledges, profile="swordsman"):
        behaviour = behaviours.for_profile(profiles.load(profile))
        return behaviour.decide(Situation(state="Attack", dx=dx, dy=0, now=10.0, target_seen=10.0, ledges=ledges))

    def test_steps_in_when_a_hit_would_knock_it_off(self):  # Mob on the inner side, ledge close behind
        a = self.decide(40, (20, 400))
        self.assertEqual((a.kind, a.direction, a.label), ("move", "right", "stepping away from the ledge"))
        a = self.decide(-40, (400, 20))
        self.assertEqual((a.kind, a.direction), ("move", "left"))

    def test_fights_when_the_mob_is_between_it_and_the_ledge(self):  # Its hits knock the player inward
        self.assertEqual(self.decide(-40, (20, 400)).kind, "attack")

    def test_fights_far_enough_from_the_ledge(self):
        self.assertEqual(self.decide(40, (ledge_margin + 5, 400)).kind, "attack")
        self.assertEqual(self.decide(40, None).kind, "attack")  # No recorded platform

    def test_mob_overlapping_steps_in(self):  # Knocked back either way: get away from the ledge
        self.assertEqual(self.decide(0, (20, 400)).direction, "right")

    def test_too_narrow_to_help_fights_in_place(self):
        self.assertEqual(self.decide(40, (20, 2 * ledge_margin - 30)).kind, "attack")

    def test_backing_off_stops_short_of_a_ledge(self):  # Ranged: keep_distance would back it off the platform
        behaviour = behaviours.for_profile(profiles.from_dict("test", {"behaviour": "ranged", "ranged": {"keep_distance": 200},
                                                                       "attacks": [{"key": "Ctrl", "range_x": [0, 400], "range_y": [-30, 25]}]}))
        backing = lambda ledges: behaviour.decide(Situation(state="Attack", dx=100, dy=0, now=10.0, target_seen=10.0, ledges=ledges))
        self.assertEqual(backing(None).label, "back off")
        self.assertEqual(backing((2 * ledge_margin - 10, 900)).kind, "attack")  # Not enough room behind: stand and shoot


class CalculationsTests(unittest.TestCase):  # The distances calculations hand the bot, through the router tests' stand-in recorder
    def test_ledges_from_the_feet(self):
        thread = calculations.CalculationThread()
        with mock.patch.object(values, "nav_jump_height", 100):
            mapper = RouterTests.mapper(None, (1060, 520))
            self.assertEqual(thread.ledges(mapper), (160, 40))
            mapper.feet = (1060, 400)  # In the air, off any platform
            self.assertIsNone(thread.ledges(mapper))


if __name__ == "__main__":
    unittest.main()
