# Tests for retreating when low on potions: the bot noticing it from the quickslot, calculations heading for a safe spot on the recorded
# map, and botting stopping there

import unittest
from unittest import mock

from data import values
from data.rects import Rect
from process import bot, calculations
from tests.test_route_planner import GROUND, LEDGE, LINES, TOP, RouterTests
from tools import map_recorder


def player_at(x, feet):
    return Rect("Player", "blue", x - 25, feet - 66, x + 25, feet, 1)


class TriggerTests(unittest.TestCase):
    def setUp(self):
        self.thread = bot.BotThread()
        for name, value in (("hp_potion_key", "Delete"), ("hp_potion_threshold", 300), ("mp_potion_key", "End"), ("mp_potion_threshold", 0),
                            ("retreating", False), ("retreat_arrived", False), ("retreat_status", None), ("stats_read_id", 0)):
            patcher = mock.patch.object(values, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for patcher in (mock.patch.object(bot, "retreat_at", 1), mock.patch.object(bot, "potion_confirm_reads", 2)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def read(self, quickslot, times=1):  # Fresh quickslot readings, each checked as the bot loop would
        for _ in range(times):
            values.stats_read_id += 1
            with mock.patch.object(values, "quickslot", quickslot):
                self.thread.check_potions()

    def test_down_to_one_retreats(self):
        self.read({"Delete": 2}, 3)
        self.assertFalse(values.retreating)
        self.read({"Delete": 1})
        self.assertFalse(values.retreating)  # One reading could be a misread
        self.read({"Delete": 1})
        self.assertTrue(values.retreating)
        self.assertIn("safe spot", values.retreat_status)

    def test_only_fresh_readings_count(self):
        self.read({"Delete": 1})
        with mock.patch.object(values, "quickslot", {"Delete": 1}):
            self.thread.check_potions()  # The same reading again
        self.assertFalse(values.retreating)

    def test_unknown_counts_and_unused_keys_dont(self):
        self.read(None, 3)  # Quickslot hidden
        self.read({"Delete": None}, 3)  # Count not readable
        self.read({"Delete": 50, "End": 0}, 3)  # MP potions out, but auto potion doesn't use them (no threshold)
        self.assertFalse(values.retreating)

    def test_stops_botting_once_there(self):
        self.thread.is_running = True
        values.retreating = True
        self.thread.finish_retreat()
        self.assertFalse(self.thread.is_running)
        self.assertFalse(values.retreating)
        self.assertIn("Stopped", values.retreat_status)


class SafeSpotTests(unittest.TestCase):  # test_route_planner's made-up map (map = screen coords), mobs all over the ground floor
    def setUp(self):
        self.thread = calculations.CalculationThread()
        for name, value in (("nav_jump_height", 100), ("retreat_arrived", False), ("planned_route", None)):
            patcher = mock.patch.object(values, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def mapper(self, feet, learned=True):
        mapper = RouterTests.mapper(None, feet)
        platforms = map_recorder.PlatformMap()
        for line in LINES:
            for x in range(line[0][0], line[-1][0] + 1, 4):
                platforms.add_ground(x, line[0][1])
        if learned:
            platforms.see((0, 0, 1366, 768), [(0, 1200, 600)], map_recorder.learn_time * 2)  # Watched a while, mobs on the floor throughout
        mapper.platforms = platforms
        return mapper

    def test_heads_for_a_safe_platform(self):
        result = self.thread.retreat(player_at(100, 600), [], self.mapper((100, 600)), True, False)
        line, x = self.thread.retreat_spot
        self.assertIn(line, (LEDGE, TOP))  # Not the floor, where the mobs are
        self.assertEqual(result.state, "Navigate")
        self.assertFalse(values.retreat_arrived)
        self.assertIsNotNone(values.planned_route)  # Drawn with the overlay's Route option

    def test_walks_to_the_middle_then_arrives(self):
        result = self.thread.retreat(player_at(920, 520), [], self.mapper((920, 520)), True, False)  # On the ledge, near its end
        _, x = self.thread.retreat_spot
        self.assertAlmostEqual(x, 1000, delta=4)
        self.assertEqual((result.state, result.route), ("Navigate", "walk"))
        self.assertGreater(result.dx, 0)
        self.assertFalse(values.retreat_arrived)
        self.thread.retreat(player_at(1000, 520), [], self.mapper((1000, 520)), True, False)
        self.assertTrue(values.retreat_arrived)

    def test_nowhere_known_to_be_safe_stops_where_it_is(self):  # Not watched long enough to know yet
        self.thread.retreat(player_at(100, 600), [], self.mapper((100, 600), learned=False), True, False)
        self.assertTrue(values.retreat_arrived)

    def test_mobs_are_ignored(self):  # A mob in reach isn't fought on the way
        mob = Rect("Mob", "red", 130, 560, 170, 600, 1)
        result = self.thread.retreat(player_at(100, 600), [mob], self.mapper((100, 600)), True, False)
        self.assertNotEqual(result.state, "Attack")


if __name__ == "__main__":
    unittest.main()
