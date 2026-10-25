# Tests for the navigation planner, using made-up scenes in screen coordinates (y grows downwards)

import unittest
from unittest import mock

from data import profiles
from data.rects import Rect
from process import behaviours, executor, navigation
from process.behaviours import Situation
from tools import keyboard


def platform(x1, x2, top):
    return Rect("Platform", "brown", x1, top, x2, top + 20, 1)


def mob_on(x, feet):
    return Rect("Mob", "red", x - 20, feet - 40, x + 20, feet, 1)


def player_at(x, feet=600):
    return Rect("Player", "blue", x - 25, feet - 66, x + 25, feet, 1)


GROUND = platform(0, 1000, 600)  # The player stands on this, feet at y 600


class PlanTests(unittest.TestCase):
    def test_attacks_mob_on_same_platform(self):
        p = navigation.plan(player_at(500), [GROUND, mob_on(620, 600)], 100)
        self.assertEqual((p.state, p.dx), ("Attack", 120))

    def test_jumps_up_to_mob_above(self):
        upper = platform(300, 450, 520)  # 80 above the feet
        p = navigation.plan(player_at(500), [GROUND, upper, mob_on(400, 520)], 100)
        self.assertEqual((p.state, p.route, p.target), ("Navigate", "up", upper))

    def test_prefers_path_towards_the_mob(self):
        left, right = platform(300, 450, 520), platform(520, 670, 520)  # right is closer to the player
        self.assertIs(navigation.plan(player_at(500), [GROUND, left, right], 100).target, right)  # No mob: nearest
        p = navigation.plan(player_at(500), [GROUND, left, right, mob_on(120, 600 - 200)], 100)  # Mob far left, higher up
        self.assertIs(p.target, left)

    def test_respects_jump_height(self):
        high = platform(600, 800, 480)  # 120 above the feet
        self.assertIsNone(navigation.plan(player_at(500), [GROUND, high], 100).state)
        self.assertIs(navigation.plan(player_at(500), [GROUND, high], 150).target, high)

    def test_ladder_reachable_above(self):
        ladder = Rect("Ladder", "yellow", 900, 400, 910, 550, 1)
        p = navigation.plan(player_at(500), [GROUND, ladder], 100)
        self.assertEqual((p.route, p.on_ladder), ("up", True))

    def test_drops_to_mob_below(self):
        lower = platform(100, 400, 700)
        p = navigation.plan(player_at(500), [GROUND, lower, mob_on(220, 700)], 100)
        self.assertEqual((p.state, p.route, p.target, p.dx), ("Navigate", "down", lower, 385 - 500))  # Walk inside its right edge first
        p = navigation.plan(player_at(250), [GROUND, lower, mob_on(220, 700)], 100)
        self.assertEqual(p.dx, 0)  # Over it: drop now

    def test_walks_to_mob_across_a_gap(self):
        other = platform(1100, 1300, 600)
        p = navigation.plan(player_at(500), [GROUND, other, mob_on(1220, 600)], 100)
        self.assertEqual((p.state, p.route, p.dx), ("Navigate", "walk", 720))

    def test_explores_down_when_nothing_above(self):
        lower = platform(100, 400, 700)
        p = navigation.plan(player_at(500), [GROUND, lower], 100)
        self.assertEqual((p.route, p.target), ("down", lower))

    def test_attacks_any_mob_without_a_platform(self):
        p = navigation.plan(player_at(500), [mob_on(800, 400)], 100)
        self.assertEqual(p.state, "Attack")

    def test_search_without_player_and_idle_when_nothing_to_do(self):
        self.assertEqual(navigation.plan(None, [GROUND], 100).state, "Search")
        self.assertIsNone(navigation.plan(player_at(500), [GROUND], 100).state)


class RouteBehaviourTests(unittest.TestCase):
    def decide(self, **situation):
        return behaviours.for_profile(profiles.load("spearman")).decide(Situation(state="Navigate", **situation))

    def test_down_route(self):
        self.assertEqual(self.decide(route="down", dx=0, dy=-100).kind, "drop")
        a = self.decide(route="down", dx=-115, dy=-100)
        self.assertEqual((a.kind, a.direction), ("move", "left"))

    def test_walk_route_never_jumps(self):
        self.assertEqual(self.decide(route="walk", dx=30, dy=0).kind, "move")
        self.assertEqual(self.decide(route="walk", dx=720).kind, "mobility")  # Far: dash

    def test_drop_presses_down_and_jump(self):
        presses = []
        e = executor.Executor(profiles.load("spearman"))
        with mock.patch.object(keyboard, "PressKey", lambda k: presses.append(k)), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: None), mock.patch("time.sleep"):
            e.run(behaviours.Action("drop"))
        self.assertEqual(presses, [keyboard.VK_DOWN, keyboard.VK_MENU])


if __name__ == "__main__":
    unittest.main()
