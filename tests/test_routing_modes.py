# Tests for the routing presets on test_route_planner's made-up map (map = screen coords): the ground at y 600, a ledge at 520 reached
# by a jump, and a top platform at 300 reached by a rope

import unittest
from unittest import mock

from data import values
from data.rects import Rect
from process import calculations
from tests.test_route_planner import GROUND, LEDGE, TOP, RouterTests


def player_at(x, feet):
    return Rect("Player", "blue", x - 25, feet - 66, x + 25, feet, 1)


def mob_at(x, feet):
    return Rect("Mob", "red", x - 20, feet - 40, x + 20, feet, 0.9)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.thread = calculations.CalculationThread()
        self.clock = [100.0]
        for target, name, value in ((values, "nav_jump_height", 100), (values, "planned_route", None), (values, "bot_active", True),
                                    (calculations.time, "time", lambda: self.clock[0])):
            patcher = mock.patch.object(target, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.mapper = RouterTests.mapper(None, (100, 600))
        self.mapper.map_id = "test"

    def plan(self, mode, x, feet, mobs=(), at=0.0):
        self.clock[0] = 100.0 + at
        self.mapper.feet = (x, feet)
        router = lambda goal: self.thread.route_step(goal, self.mapper)
        return self.thread.keep_to_platforms(mode, player_at(x, feet), list(mobs), self.mapper, True, False, [], router)

    def heading(self, result):  # The platform the plan is taking it to, by its height
        return round(result.target.top_at(result.target.center_x)) if result.target is not None else None


class PatrolTests(RoutingTests):
    def test_climbs_level_by_level_then_drops_straight_to_the_bottom(self):
        self.assertIsNone(self.plan("patrol", 100, 600).state)  # Just cleared: watches a moment first
        up = self.plan("patrol", 100, 600, at=calculations.patrol_linger + 0.1)
        self.assertEqual(up.state, "Navigate")
        self.assertEqual(self.thread.patrol_goal[1], 520)  # The ledge: the next level up, not the top
        self.plan("patrol", 1000, 520, at=2)  # Arrived on the ledge
        self.plan("patrol", 1000, 520, at=4)
        self.assertEqual(self.thread.patrol_goal[1], 300)  # Then the top
        self.plan("patrol", 600, 300, at=6)
        self.plan("patrol", 600, 300, at=8)  # Nothing higher: turns round, for the bottom, not the ledge on the way
        self.assertEqual((self.thread.patrol_direction, self.thread.patrol_goal[1]), ("down", 600))
        self.plan("patrol", 300, 600, at=10)
        self.plan("patrol", 300, 600, at=12)  # The bottom: up again, level by level
        self.assertEqual((self.thread.patrol_direction, self.thread.patrol_goal[1]), ("up", 520))

    def test_leaves_a_lone_mob_far_off_for_the_next_level(self):  # Climbing beats a walk to the platform's edge for one mob
        self.assertIsNone(self.plan("patrol", 100, 600, [mob_at(900, 600)]).state)  # 780 px off: treated as cleared
        result = self.plan("patrol", 100, 600, [mob_at(900, 600)], at=calculations.patrol_linger + 0.1)
        self.assertEqual((result.state, self.thread.patrol_goal[1]), ("Navigate", 520))
        self.assertEqual(self.plan("patrol", 100, 600, [mob_at(220, 600)], at=3).state, "Attack")  # A lone one close by: fought

    def test_goes_after_two_or_more_wherever_they_are(self):
        result = self.plan("patrol", 100, 600, [mob_at(850, 600), mob_at(900, 600)])
        self.assertEqual((result.state, result.target.center_x), ("Attack", 850))  # Going over to them
        self.assertIsNone(self.thread.patrol_goal)

    def test_on_the_way_down_only_fights_what_its_already_in_reach_of(self):
        self.thread.patrol_direction, self.thread.patrol_goal = "down", (600, 600)
        with mock.patch.object(values, "nav_attack_range", 75):
            passing = self.plan("patrol", 1000, 520, [mob_at(1050, 520), mob_at(1060, 520)])
            self.assertEqual(passing.state, "Attack")  # Right there: in the way
            far = self.plan("patrol", 1000, 520, [mob_at(880, 520), mob_at(1120, 520)], at=1)  # 100 px off, either side
            self.assertNotEqual(far.state, "Attack")  # Not going after them: on down

    def test_fights_the_platform_its_on_first(self):
        result = self.plan("patrol", 100, 600, [mob_at(160, 600), mob_at(1000, 520)], at=5)
        self.assertEqual((result.state, result.target.center_x), ("Attack", 160))
        self.assertIsNone(self.thread.patrol_goal)  # Not moving on while there's something to fight

    def test_mobs_on_other_platforms_dont_pull_it_away(self):
        self.plan("patrol", 100, 600, [mob_at(1000, 520)])
        result = self.plan("patrol", 100, 600, [mob_at(1000, 520)], at=calculations.patrol_linger + 0.1)
        self.assertEqual(result.state, "Navigate")  # On to the next level by its own choice
        self.assertEqual(self.thread.patrol_goal[1], 520)


class StayTests(RoutingTests):
    def test_only_fights_on_its_home_platform(self):
        self.plan("stay", 1000, 520)  # Starts on the ledge: home
        self.assertEqual(self.plan("stay", 1000, 520, [mob_at(1060, 520)]).state, "Attack")
        result = self.plan("stay", 1000, 520, [mob_at(300, 600)])  # A mob on the ground below: not its platform
        self.assertNotEqual(result.state, "Attack")
        self.assertIsNone(result.state)  # Waits

    def test_knocked_off_goes_back(self):
        self.plan("stay", 1000, 520)
        result = self.plan("stay", 700, 600, [mob_at(760, 600)])  # Fell to the ground, a mob right there
        self.assertNotEqual(result.state, "Attack")
        self.assertEqual((result.state, self.heading(result)), ("Navigate", 520))  # Back up to the ledge

    def test_home_taken_again_when_botting_restarts_or_mode_picked(self):
        with mock.patch.object(values, "routing_mode", "stay"):
            self.thread.sync_mode()
            self.plan("stay", 1000, 520)
            self.assertEqual(self.thread.home[1], (1000, 520))
            self.thread.sync_mode()  # Botting carries on: home kept
            self.assertIsNotNone(self.thread.home)
            values.bot_active = False
            self.thread.sync_mode()  # Stopped...
            values.bot_active = True
            self.thread.sync_mode()  # ...and started again: home taken afresh where it is now
            self.assertIsNone(self.thread.home)
            self.plan("stay", 300, 600)
            self.assertEqual(self.thread.home[1], (300, 600))
            values.routing_mode = "patrol"
            self.assertEqual(self.thread.sync_mode(), "patrol")
            self.assertIsNone(self.thread.home)


if __name__ == "__main__":
    unittest.main()
