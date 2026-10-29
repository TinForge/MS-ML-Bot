# Tests for when the bot goes looking for mobs on other platforms

import unittest
from types import SimpleNamespace
from unittest import mock

from data import config, values
from process import calculations
from tools import movement


class ExploreTests(unittest.TestCase):
    def setUp(self):
        self.clock = [100.0]
        patcher = mock.patch("time.time", lambda: self.clock[0])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.thread = calculations.CalculationThread()
        self.player = object()
        patcher = mock.patch.object(values, "randomizer_active", True)  # Exploring is part of Random Behaviour
        patcher.start()
        self.addCleanup(patcher.stop)

    def explore(self, mobs, feet=(500, 600), state=movement.GROUND):
        return self.thread.explore(mobs, self.player, SimpleNamespace(feet=feet, state=state))

    def test_stays_put_without_random_behaviour(self):
        values.randomizer_active = False
        self.explore(True)
        self.clock[0] += config.explore_delay + 5
        self.assertIsNone(self.explore(False))

    def test_waits_a_few_seconds_without_mobs(self):
        self.assertIsNone(self.explore(True))
        self.clock[0] += config.explore_delay - 0.5
        self.assertIsNone(self.explore(False))
        self.clock[0] += 1
        self.assertEqual(self.explore(False), "up")

    def test_each_platform_reached_waits_again(self):
        self.explore(True)
        self.clock[0] += config.explore_delay + 0.1
        self.assertEqual(self.explore(False), "up")
        self.clock[0] += 1
        self.assertEqual(self.explore(False, feet=(500, 450), state=movement.LADDER), "up")  # Still climbing
        self.assertIsNone(self.explore(False, feet=(500, 380)))  # Standing on the platform above
        self.clock[0] += config.explore_delay - 0.5
        self.assertIsNone(self.explore(False, feet=(520, 380)))
        self.clock[0] += 1
        self.assertEqual(self.explore(False, feet=(520, 380)), "up")

    def test_jumps_off_a_climb_that_stopped_rising(self):  # e.g. a rope with nothing at the top
        from process import navigation
        rope = navigation.Plan("Navigate", object(), route="climb")
        player = SimpleNamespace(center_x=200)
        mapper = SimpleNamespace(feet=(500, 400))
        self.assertEqual(self.thread.unstick_climb(rope, player, mapper).route, "climb")
        self.clock[0] += 0.5
        mapper.feet = (500, 380)  # Rising
        self.assertEqual(self.thread.unstick_climb(navigation.Plan("Navigate", object(), route="climb"), player, mapper).route, "climb")
        self.clock[0] += calculations.climb_stuck_time + 0.1  # Then stuck at 380
        result = self.thread.unstick_climb(navigation.Plan("Navigate", object(), route="climb"), player, mapper)
        self.assertEqual(result.route, "jump_off")

    def test_platform_given_up_on_after_failed_jumps(self):
        from data.rects import Rect
        from process import navigation
        ledge = Rect("Platform", "brown", 460, 520, 560, 540, 1)
        jumping = lambda: navigation.Plan("Navigate", ledge, route="up", dx=0)
        self.thread.watch_jumps(jumping(), None)
        self.assertEqual(self.thread.unreachable_platforms([ledge], None), [])
        self.clock[0] += calculations.jump_give_up + 0.1
        self.thread.watch_jumps(jumping(), None)
        self.assertEqual(self.thread.unreachable_platforms([ledge], None), [ledge])
        self.clock[0] += calculations.unreachable_time + 0.1
        self.assertEqual(self.thread.unreachable_platforms([ledge], None), [])  # Tried again later

    def test_walking_to_a_platform_is_not_failing_to_jump(self):
        from data.rects import Rect
        from process import navigation
        ledge = Rect("Platform", "brown", 460, 520, 560, 540, 1)
        walking = lambda: navigation.Plan("Navigate", ledge, route="up", dx=300)
        self.thread.watch_jumps(walking(), None)
        self.clock[0] += calculations.jump_give_up + 1
        self.thread.watch_jumps(walking(), None)
        self.assertEqual(self.thread.unreachable_platforms([ledge], None), [])

    def test_keeps_climbing_a_moment_at_the_top(self):  # The platform overlaps the rope's top: ground shows before it has stepped off
        from process import navigation
        climb = lambda: navigation.Plan("Navigate", object(), route="climb")
        self.assertEqual(self.thread.finish_climb(climb()).route, "climb")
        self.clock[0] += 0.1
        at_top = self.thread.finish_climb(navigation.Plan("Attack", object()))  # A mob on the platform, before it's off the rope
        self.assertEqual((at_top.state, at_top.route), ("Navigate", "climb"))
        self.clock[0] += calculations.top_hold
        self.assertEqual(self.thread.finish_climb(navigation.Plan("Attack", object())).state, "Attack")
        self.thread.finish_climb(climb())
        self.assertEqual(self.thread.finish_climb(navigation.Plan("Navigate", object(), route="jump_off", dx=1)).route, "jump_off")
        self.assertEqual(self.thread.finish_climb(navigation.Plan("Attack", object())).state, "Attack")  # Jumped off: no carrying on

    def test_mobs_coming_into_sight_stop_it(self):
        self.explore(True)
        self.clock[0] += config.explore_delay + 0.1
        self.explore(False)
        self.assertIsNone(self.explore(True))


if __name__ == "__main__":
    unittest.main()
