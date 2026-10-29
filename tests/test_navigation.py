# Tests for the navigation planner, using made-up scenes in screen coordinates (y grows downwards)

import os
import unittest
from unittest import mock

from data import profiles
from data.rects import PlatformLine, Rect
from process import behaviours, executor, navigation
from process.behaviours import Situation
from tools import keyboard

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "profiles")  # Not your edited profiles


def setUpModule():
    patcher = mock.patch.object(profiles, "folder", FIXTURES)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def platform(x1, x2, top):
    return Rect("Platform", "brown", x1, top, x2, top + 20, 1)


def mob_on(x, feet):
    return Rect("Mob", "red", x - 20, feet - 40, x + 20, feet, 1)


def player_at(x, feet=600):
    return Rect("Player", "blue", x - 25, feet - 66, x + 25, feet, 1)


GROUND = platform(0, 1000, 600)  # The player stands on this, feet at y 600


class PlanTests(unittest.TestCase):
    def test_slope_counts_as_one_platform(self):  # Recorded ground: a slope rising 100 px to the right
        slope = PlatformLine([(0, 650), (400, 650), (800, 550), (1000, 550)])
        p = navigation.plan(player_at(600, 600), [slope, mob_on(900, 550)], 100)
        self.assertEqual((p.state, p.platform), ("Attack", slope))  # Mob higher up the same slope: walk and attack, no jumping

    def test_slope_height_along_the_line(self):
        slope = PlatformLine([(0, 650), (400, 650), (800, 550)])
        self.assertEqual([slope.top_at(x) for x in (-50, 200, 600, 800, 900)], [650, 650, 600, 550, 550])

    def test_attacks_mob_on_same_platform(self):
        p = navigation.plan(player_at(500), [GROUND, mob_on(620, 600)], 100)
        self.assertEqual((p.state, p.dx), ("Attack", 100))  # To the mob's nearer edge: its box is 40 wide

    def test_wide_mob_is_in_reach_by_its_edge(self):  # Measured centre to centre it would be 140 away, and the bot would walk into it
        wide = Rect("Mob", "red", 590, 520, 690, 600, 1)
        p = navigation.plan(player_at(500), [GROUND, wide], 100)
        self.assertEqual(p.dx, 90)
        overlapping = navigation.plan(player_at(500), [GROUND, Rect("Mob", "red", 470, 560, 550, 600, 1)], 100)
        self.assertEqual(overlapping.dx, 0)  # Attacked whichever way the character faces

    def test_jumps_up_to_mob_above(self):
        upper = platform(300, 450, 520)  # 80 above the feet
        p = navigation.plan(player_at(500), [GROUND, upper, mob_on(400, 520)], 100)
        self.assertEqual((p.state, p.route, p.target), ("Navigate", "up", upper))

    def test_prefers_path_towards_the_mob(self):
        left, right = platform(300, 450, 520), platform(520, 670, 520)  # right is closer to the player
        p = navigation.plan(player_at(500), [GROUND, left, right, platform(0, 250, 400), mob_on(120, 400)], 100)  # Mob far left, higher up
        self.assertIs(p.target, left)

    def test_respects_jump_height(self):
        high = platform(600, 800, 480)  # 120 above the feet
        scene = [GROUND, high, mob_on(700, 480)]
        self.assertEqual(navigation.plan(player_at(500), scene, 100).route, "walk")  # Out of reach: walk towards it
        self.assertIs(navigation.plan(player_at(500), scene, 150).target, high)

    def test_ladder_reachable_above(self):
        ladder = Rect("Ladder", "yellow", 900, 400, 910, 550, 1)
        top = platform(850, 1000, 380)
        p = navigation.plan(player_at(500), [GROUND, ladder, top, mob_on(905, 380)], 100)  # Mob up where the ladder leads
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

    def test_never_climbs_for_a_mob_floating_above_this_platform(self):  # A flying mob, or a box drawn above its feet: walk, no rope
        ladder = Rect("Ladder", "yellow", 520, 400, 530, 550, 1)
        p = navigation.plan(player_at(500), [platform(0, 560, 600), platform(570, 1000, 600), ladder, mob_on(800, 550)], 100)
        self.assertEqual(p.route, "walk")

    def test_climbs_while_hanging_on_a_rope(self):
        rope, top = Rect("Ladder", "yellow", 492, 380, 508, 590, 1), platform(400, 700, 380)  # Feet positions recorded climbing it
        p = navigation.plan(player_at(500, feet=500), [GROUND, rope, top, mob_on(600, 380)], 100)  # Halfway up, mob on top
        self.assertEqual((p.state, p.route), ("Navigate", "climb"))
        self.assertEqual(navigation.plan(player_at(500, feet=500), [GROUND, rope, top], 100).route, "climb")  # Even with no mobs
        at_top = navigation.plan(player_at(500, feet=380), [GROUND, rope, top, mob_on(600, 380)], 100)
        self.assertEqual(at_top.state, "Attack")  # Off the rope onto the platform: fight
        at_foot = navigation.plan(player_at(500), [GROUND, rope, top], 100)
        self.assertIsNone(at_foot.route)  # Standing on the ground beside it, with nothing to go up for

    def test_movement_tracker_can_rule_out_a_rope(self):  # Standing where no platform is recorded, next to a rope
        rope = Rect("Ladder", "yellow", 492, 380, 508, 590, 1)
        self.assertEqual(navigation.plan(player_at(500, feet=500), [rope], 100).route, "climb")
        self.assertIsNone(navigation.plan(player_at(500, feet=500), [rope], 100, standing=True).route)

    def test_tracker_knows_an_unrecorded_rope(self):  # Hanging on a rope that was never recorded: climb, don't walk
        p = navigation.plan(player_at(500, feet=450), [GROUND, mob_on(700, 300)], 100, on_rope=True)
        self.assertEqual(p.route, "climb")
        standing = navigation.plan(player_at(500, feet=600), [GROUND, mob_on(700, 600)], 100, on_rope=True)
        self.assertEqual(standing.state, "Attack")  # Ground under the feet: off the rope, whatever the tracker still says

    def test_jumps_off_a_rope_toward_a_mob_below(self):
        rope = Rect("Ladder", "yellow", 492, 380, 508, 590, 1)
        p = navigation.plan(player_at(500, feet=450), [GROUND, rope, mob_on(300, 600)], 100, on_rope=True)
        self.assertEqual((p.route, p.dx), ("jump_off", -1))

    def test_takes_the_rope_when_a_platform_jump_keeps_failing(self):
        ledge, rope, top = platform(460, 560, 520), Rect("Ladder", "yellow", 642, 380, 658, 590, 1), platform(400, 900, 380)
        scene = [GROUND, ledge, rope, top, mob_on(800, 380)]
        self.assertIs(navigation.plan(player_at(500), scene, 100).target, ledge)  # Nearest way up
        self.assertIs(navigation.plan(player_at(500), scene, 100, skip=[ledge]).target, rope)

    def test_lines_up_under_a_rope_before_jumping(self):
        rope, top = Rect("Ladder", "yellow", 532, 380, 548, 550, 1), platform(400, 700, 380)
        far = navigation.plan(player_at(500), [GROUND, rope, top, mob_on(600, 380)], 100)
        self.assertEqual((far.route, far.on_ladder, far.dx), ("up", True, 40))  # To the rope's middle, not its edge
        close = navigation.plan(player_at(530), [GROUND, rope, top, mob_on(600, 380)], 100)
        self.assertEqual(close.dx, 0)

    def test_explores_up_then_down_when_no_mobs(self):
        rope, lower = Rect("Ladder", "yellow", 532, 400, 548, 550, 1), platform(100, 800, 700)
        self.assertIsNone(navigation.plan(player_at(500), [GROUND, rope, lower], 100).state)  # Not exploring: stay put
        up = navigation.plan(player_at(500), [GROUND, rope, lower], 100, explore="up")
        self.assertEqual((up.route, up.on_ladder), ("up", True))
        down = navigation.plan(player_at(500), [GROUND, rope, lower], 100, explore="down")
        self.assertEqual((down.route, down.target), ("down", lower))
        self.assertIsNone(navigation.plan(player_at(500), [GROUND, lower], 100, explore="up").state)  # No way up

    def test_stays_put_without_mobs(self):  # It used to climb the nearest ladder or drop down for no reason
        ladder, lower = Rect("Ladder", "yellow", 520, 400, 530, 550, 1), platform(100, 400, 700)
        self.assertIsNone(navigation.plan(player_at(500), [GROUND, ladder, lower], 100).state)

    def test_never_climbs_for_a_mob_at_the_same_height(self):  # Another platform at the same height (e.g. past a gap in the recording)
        ladder, beside = Rect("Ladder", "yellow", 520, 400, 530, 550, 1), platform(1100, 1400, 600)
        p = navigation.plan(player_at(500), [GROUND, ladder, beside, mob_on(1200, 600)], 100)
        self.assertEqual((p.route, p.dx > 0), ("walk", True))

    def test_prefers_closest_mob_on_the_same_level(self):
        near_above, far_level = mob_on(540, 560), mob_on(620, 600)  # Without a platform under the player every mob counts
        self.assertIs(navigation.plan(player_at(500), [near_above, far_level], 100).target, far_level)

    def test_aims_at_the_nearest_mob_in_the_chosen_direction(self):  # That's the one an attack that way hits
        near, far = mob_on(560, 600), mob_on(640, 600)
        self.assertIs(navigation.plan(player_at(500), [GROUND, far, near], 100, previous=far).target, near)  # Even when the far one was last

    def test_crowd_measures_to_each_mobs_near_edge_and_crosses_platform_pieces(self):
        piece, next_piece = platform(0, 560, 600), platform(570, 1000, 600)  # One platform recorded in two pieces
        target, beyond = mob_on(540, 600), mob_on(640, 600)  # 40 px wide boxes
        p = navigation.plan(player_at(500), [piece, next_piece, target, beyond], 100)
        self.assertEqual(p.crowd, [(20, p.dy), (120, p.dy)])  # Edges 20 px nearer than centres; the mob on the next piece is included
        on_top = navigation.plan(player_at(500), [piece, mob_on(510, 600)], 100)
        self.assertEqual(on_top.crowd[0][0], 0)  # Overlapping the player

    def test_keeps_its_target_against_a_slightly_closer_mob(self):  # Stops it flipping between two similar mobs on either side
        left, right = mob_on(430, 600), mob_on(560, 600)  # Edges 50 and 40 away
        self.assertIs(navigation.plan(player_at(500), [GROUND, left, right], 100).target, right)
        self.assertIs(navigation.plan(player_at(500), [GROUND, left, right], 100, previous=left).target, left)
        nearer = mob_on(522, 600)  # Edge 2 away, 48 nearer than the old target: more than the stickiness, so it takes over
        self.assertIs(navigation.plan(player_at(500), [GROUND, left, nearer], 100, previous=left).target, nearer)

    def test_size_weight(self):
        small, big = mob_on(400, 600), Rect("Mob", "red", 560, 500, 680, 600, 1)  # Edges 80 and 60 away; big is 120 wide
        self.assertIs(navigation.plan(player_at(500), [GROUND, small, big], 100).target, big)  # Nearer edge, and bigger
        with mock.patch.object(navigation, "size_weight", -1):  # Prefer smaller mobs
            self.assertIs(navigation.plan(player_at(500), [GROUND, small, big], 100).target, small)

    def test_prefers_the_direction_with_more_mobs(self):
        lone, group = mob_on(440, 600), [mob_on(580, 600), mob_on(620, 600), mob_on(640, 600)]  # The lone one is a bit closer
        self.assertIs(navigation.plan(player_at(500), [GROUND, lone] + group, 100, clump_range=150).target, group[0])
        self.assertIs(navigation.plan(player_at(500), [GROUND, lone] + group, 100, clump_range=0).target, lone)  # No mobbing attack

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
