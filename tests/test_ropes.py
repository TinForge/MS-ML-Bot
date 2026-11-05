# Tests for getting onto ropes: jumping for them as high as routes count on, lining up without pacing, giving up on ones it can't
# catch, and carrying on climbing while the rope hides the nametag

import unittest
from unittest import mock

from data import profiles, values
from data.rects import PlatformLine, Rect
from process import behaviours, calculations, executor, navigation
from process.behaviours import Situation
from tests.test_behaviours import FIXTURES
from tests.test_route_planner import GROUND, LINES, ROPE, TOP, RouterTests
from tools import keyboard
from tools.route_planner import RoutePlanner, rope_extra_reach


def setUpModule():  # Fixed copies of the profiles, as in test_behaviours
    patcher = mock.patch.object(profiles, "folder", FIXTURES)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def rope(dx, dy, now=10.0, behaviour=None):
    behaviour = behaviour or behaviours.for_profile(profiles.load("swordsman"))
    return behaviour.decide(Situation(state="Navigate", route="up", dx=dx, dy=dy, on_ladder=True, now=now))


class RopeJumpTests(unittest.TestCase):
    def test_jumps_for_a_rope_as_high_as_routes_count_on(self):  # The hands catch it above the feet
        height = profiles.load("swordsman").platform_height
        self.assertEqual(rope(0, height + rope_extra_reach - 5).label, "jump onto the rope")
        self.assertEqual(rope(40, height + rope_extra_reach - 5).label, "running jump onto the rope")
        self.assertEqual(rope(0, height + rope_extra_reach + 5).label, "platform out of reach")

    def test_platforms_still_only_as_high_as_the_jump(self):
        b = behaviours.for_profile(profiles.load("swordsman"))
        height = b.profile.platform_height
        a = b.decide(Situation(state="Navigate", route="up", dx=0, dy=height + 10, on_ladder=False, now=10.0))
        self.assertEqual(a.label, "platform out of reach")

    def test_taps_into_line_instead_of_walking_past(self):  # Walking overshoots, then it walked back: pacing under the rope
        b = behaviours.for_profile(profiles.load("swordsman"))
        high = b.profile.platform_height + rope_extra_reach + 20  # Too high to jump for: lining up only
        self.assertEqual(rope(-35, high, behaviour=b).kind, "nudge")
        self.assertEqual(rope(80, high, behaviour=b).kind, "move")  # Far off: walks


class GiveUpTests(unittest.TestCase):  # A rope recorded higher than it can be caught from
    def test_routes_avoid_a_rope_that_couldnt_be_caught(self):
        planner = RoutePlanner(LINES, [ROPE], jump_height=100)
        self.assertEqual([h.kind for h in planner.route(GROUND, 100, TOP)], ["rope"])
        self.assertIsNone(planner.route(GROUND, 100, TOP, avoid={("rope", 0)}))  # The only way up

    def test_trying_the_same_rope_too_long_marks_it(self):
        thread = calculations.CalculationThread()
        mapper = RouterTests.mapper(None, (600, 600))
        ladder = Rect("Ladder", "yellow", 592, 300, 608, 590, 1)
        trying = navigation.Plan("Navigate", ladder, route="up", dx=0, on_ladder=True)
        clock = [100.0]
        with mock.patch.object(calculations.time, "time", lambda: clock[0]):
            thread.watch_jumps(trying, mapper)
            clock[0] += calculations.jump_give_up + 0.1
            thread.watch_jumps(trying, mapper)
            self.assertIn(("rope", 0), thread.unreachable_lines(mapper, (0, 0)))


class HiddenOnRopeTests(unittest.TestCase):  # The rope's art covers the nametag as it's caught
    def setUp(self):
        self.thread = calculations.CalculationThread()
        self.thread.last_seen = (575, 534, 625, 600)
        self.ladder = Rect("Ladder", "yellow", 592, 300, 608, 590, 1)

    def plan(self, result, seen):
        with mock.patch.object(values, "player_rect", (575, 534, 625, 600) if seen else None):
            return self.thread.hidden_on_rope(result)

    def test_keeps_climbing_once_the_nametag_is_hidden(self):
        jumping = navigation.Plan("Navigate", self.ladder, route="up", dx=0, on_ladder=True)
        self.plan(jumping, seen=True)  # Jumping at the rope from under it
        standing = navigation.Plan("Navigate", self.ladder, route="up", dx=0, dy=10, on_ladder=True)  # What the old position would say
        self.assertEqual(self.plan(standing, seen=False).route, "climb")

    def test_running_jump_counts_too(self):
        self.plan(navigation.Plan("Navigate", self.ladder, route="up", dx=40, on_ladder=True), seen=True)
        self.assertEqual(self.plan(navigation.Plan("Navigate", self.ladder, route="up", dx=40, on_ladder=True), seen=False).route, "climb")

    def test_hidden_elsewhere_carries_on_as_planned(self):  # A mob over the nametag while walking: nothing to do with ropes
        walking = navigation.Plan("Navigate", None, route="walk", dx=-300)
        self.plan(walking, seen=True)
        self.assertEqual(self.plan(walking, seen=False).route, "walk")


class StepOffTests(unittest.TestCase):  # Climbing holds the arrow toward the middle of the platform at the rope's top: at the top it
    # walks off, out from under the rope's art that hides the nametag
    def setUp(self):
        self.top = PlatformLine([(400, 300), (800, 300)])  # The platform the rope leads up to
        self.thread = calculations.CalculationThread()

    def climbing(self, rope_x, target=None):
        rope = Rect("Ladder", "yellow", rope_x - 8, 302, rope_x + 8, 590, 1)  # Recorded top 2 px under the platform
        return self.thread.toward_the_top(navigation.Plan("Navigate", target or rope, route="climb", on_ladder=True), [self.top])

    def test_toward_the_middle_of_the_platform_at_the_top(self):
        self.assertEqual(self.climbing(450).dx, 1)  # Rope near its left end: walk off to the right
        self.assertEqual(self.climbing(780).dx, -1)
        self.assertEqual(self.climbing(820).dx, -1)  # Hanging just past its end

    def test_kept_while_the_target_is_something_else(self):  # Hidden nametag, or the hold at the top: the plan's target may not be the rope
        self.climbing(450)
        self.assertEqual(self.climbing(450, target=Rect("Mob", "red", 0, 0, 1, 1, 1)).dx, 1)

    def test_none_without_a_platform_at_the_top(self):
        self.assertEqual(self.climbing(1200).dx, 0)
        self.assertEqual(self.thread.toward_the_top(navigation.Plan("Navigate", None, route="walk", dx=-300), [self.top]).dx, -300)

    def test_the_action_and_keys(self):
        b = behaviours.for_profile(profiles.load("swordsman"))
        climb = lambda dx: b.decide(Situation(state="Navigate", route="climb", dx=dx, on_ladder=True, now=10.0))
        self.assertEqual((climb(1).kind, climb(1).direction), ("climb", "right"))
        self.assertIsNone(climb(0).direction)
        e = executor.Executor(profiles.load("swordsman"))
        events = []
        with mock.patch.object(keyboard, "PressKey", lambda k: events.append(("down", k))), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: events.append(("up", k))), mock.patch("time.sleep"):
            e.run(behaviours.Action("climb", "left"))
            e.run(behaviours.Action("climb", "left"))
            self.assertIn(("down", keyboard.VK_LEFT), events)
            self.assertIn(("down", keyboard.VK_UP), events)
            self.assertNotIn(("up", keyboard.VK_LEFT), events)  # Held through the climb
            e.run(behaviours.Action("stop"))
        self.assertIn(("up", keyboard.VK_LEFT), events)


class RunningJumpTests(unittest.TestCase):  # Running jumps at a rope were late: a stop-and-go before the jump, and frames a little old
    def test_starts_early_by_the_lag_at_speed(self):
        b = behaviours.for_profile(profiles.load("swordsman"))
        jump = lambda dx, speed: b.decide(Situation(state="Navigate", route="up", dx=dx, dy=40, on_ladder=True, speed=speed, now=10.0))
        far = behaviours.rope_run_jump[1] + 6
        self.assertEqual(jump(far, 125.0).label, "running jump onto the rope")  # Full speed toward it: jumps 9 px sooner
        b.walk_since, b.last_walk = (None, 0, 0), (None, 0)
        self.assertNotEqual(jump(far, 0.0).label, "running jump onto the rope")  # Standing: as measured
        self.assertNotEqual(jump(far, -125.0).label, "running jump onto the rope")  # Moving away: no lead

    def keys(self, *actions):
        e = executor.Executor(profiles.load("swordsman"))
        events = []
        with mock.patch.object(keyboard, "PressKey", lambda k: events.append(("down", k))), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: events.append(("up", k))), \
                mock.patch("time.sleep", lambda t: events.append(("wait", round(t, 2)))):
            for action in actions:
                e.run(action)
        return events

    def test_jumps_at_once_when_already_walking_that_way(self):
        events = self.keys(behaviours.Action("move", "right"), behaviours.Action("move_jump", "right", up=True))
        jump = events.index(("down", keyboard.VK_MENU))  # The swordsman's jump: Alt
        between = events[events.index(("down", keyboard.VK_RIGHT)) + 1:jump]
        self.assertNotIn(("up", keyboard.VK_RIGHT), between)  # Kept walking into the jump
        self.assertNotIn(("wait", 0.15), between)  # No run-up

    def test_runs_up_from_a_standstill(self):
        events = self.keys(behaviours.Action("move_jump", "right"))
        self.assertEqual(events[:2], [("down", keyboard.VK_RIGHT), ("wait", 0.15)])


class DropTests(unittest.TestCase):  # Down on top of a rope grabs it instead of falling through
    def test_no_dropping_over_the_top_of_a_rope(self):
        planner = RoutePlanner(LINES, [ROPE], jump_height=100)  # The rope goes from the ground up to the top platform at x 600
        drops = [h for h in planner.hops[TOP] if h.kind == "drop"]
        self.assertTrue(drops)  # Still drops from the rest of it
        for hop in drops:
            self.assertFalse(hop.x1 - 1 <= ROPE["x"] <= hop.x2 + 1, (hop.x1, hop.x2))
            self.assertTrue(hop.x2 < ROPE["x"] - 30 or hop.x1 > ROPE["x"] + 30)
        bare = RoutePlanner(LINES, [], jump_height=100)  # Without the rope: anywhere along it
        self.assertTrue(any(h.x1 <= ROPE["x"] <= h.x2 for h in bare.hops[TOP] if h.kind == "drop"))


if __name__ == "__main__":
    unittest.main()
