# Tests for planning routes across a recorded map, on a made-up one (map coords, y grows downwards):
#
#   top     y 300   x 400-800                       (only by the rope)
#   ledge   y 520   x 900-1100                      (a jump from the ground)
#   ground  y 600   x 0-1200
#   rope    x 600, from feet height 590 up to 300   (from the ground to the top)

import unittest
from types import SimpleNamespace
from unittest import mock

from data import values
from data.rects import PlatformLine, Rect
from process import calculations, navigation
from tools import map_recorder
from tools.route_planner import RoutePlanner

GROUND, LEDGE, TOP = 0, 1, 2
LINES = [[(0, 600), (1200, 600)], [(900, 520), (1100, 520)], [(400, 300), (800, 300)]]
ROPE = {"x": 600, "top": 300, "bottom": 590}


def planner():
    return RoutePlanner(LINES, [ROPE], jump_height=100)


class RoutePlannerTests(unittest.TestCase):
    def test_finds_where_the_feet_are(self):
        r = planner()
        self.assertEqual((r.line_at(100, 600), r.line_at(1000, 520), r.line_at(500, 300), r.line_at(100, 450)), (GROUND, LEDGE, TOP, None))

    def test_rope_up_to_the_top(self):  # Too high to jump: the only way is the rope
        hops = planner().route(GROUND, 100, TOP)
        self.assertEqual([(h.kind, h.to) for h in hops], [("rope", TOP)])
        self.assertTrue(hops[0].x1 <= 600 <= hops[0].x2)

    def test_jump_up_to_the_ledge_and_drop_back(self):
        r = planner()
        self.assertEqual([h.kind for h in r.route(GROUND, 100, LEDGE)], ["jump"])
        down = r.route(LEDGE, 1000, GROUND)
        self.assertEqual([(h.kind, h.to) for h in down], [("drop", GROUND)])

    def test_several_hops(self):  # From the ledge to the top: down, then the rope
        self.assertEqual([h.kind for h in planner().route(LEDGE, 1000, TOP)], ["drop", "rope"])

    def test_route_points_to_draw(self):  # From the ledge: walk to the drop, land on the ground, walk to the rope, climb it
        r = planner()
        points = r.path(LEDGE, 1050, r.route(LEDGE, 1050, TOP))
        self.assertEqual(points[0], (1050, 520))  # The feet
        self.assertEqual(points[2][1], 600)  # Landed on the ground
        self.assertEqual(points[-3:], [(600, 590), (600, 300), (600, 300)])  # The rope's foot, its top, and the top platform

    def test_pieces_of_one_platform_are_walked(self):  # A gap in the recording splits the ground; a real stair step stays a jump
        lines = [[(0, 600), (500, 600)], [(520, 602), (1000, 602)], [(1004, 550), (1100, 550)]]
        r = RoutePlanner(lines, [], jump_height=100)
        self.assertTrue(r.same_platform(0, 1))
        self.assertFalse(r.same_platform(1, 2))  # 52 px up: a step to jump
        self.assertEqual([h.kind for h in r.route(0, 100, 1)], ["walk"])
        self.assertEqual([h.kind for h in r.route(0, 100, 2)], ["walk", "jump"])
        self.assertEqual(r.width(0), 1000)
        twice = RoutePlanner([[(0, 600), (500, 600)], [(200, 604), (300, 604)]], [], jump_height=100)  # Recorded twice, overlapping
        self.assertTrue(twice.same_platform(0, 1))

    def test_no_way_there(self):
        no_rope = RoutePlanner(LINES, [], jump_height=100)
        self.assertIsNone(no_rope.route(GROUND, 100, TOP))
        self.assertIsNone(planner().route(GROUND, 100, LEDGE, avoid={LEDGE}))  # Jumps at it kept failing

    def test_rope_hanging_beside_a_platform_edge(self):  # Ropes usually hang just past a platform's end
        lines = [[(0, 600), (1200, 600)], [(400, 300), (580, 300)]]  # The top ends 20 px before the rope
        r = RoutePlanner(lines, [ROPE], jump_height=100)
        self.assertEqual([h.kind for h in r.route(0, 100, 1)], ["rope"])

    def test_on_real_maps_quickly(self):  # Built in well under a second, routes in a millisecond
        import glob
        import json
        import time
        for path in glob.glob("maps/*/platforms.json")[:10]:
            with open(path) as f:
                m = map_recorder.PlatformMap.from_json(json.load(f))
            lines = m.platforms()
            if len(lines) < 2:
                continue
            started = time.perf_counter()
            r = RoutePlanner(lines, m.confirmed_ladders(), 100)
            r.routes(0, lines[0][0][0])
            self.assertLess(time.perf_counter() - started, 1.0)


class NavigationRouteTests(unittest.TestCase):  # Screen coords: the made-up map drawn as is, the player on the ground
    def player(self, x, feet=600):
        return Rect("Player", "blue", x - 25, feet - 66, x + 25, feet, 1)

    def test_follows_a_rope_step_to_a_mob_above(self):
        rope = Rect("Ladder", "yellow", 592, 300, 608, 590, 1)
        ground, top = PlatformLine(LINES[GROUND]), PlatformLine(LINES[TOP])
        mob = Rect("Mob", "red", 480, 260, 520, 300, 1)
        p = navigation.plan(self.player(100), [ground, top, mob], 100, router=lambda goal: navigation.Step("rope", rope))
        self.assertEqual((p.route, p.target, p.on_ladder, p.dx), ("up", rope, True, 500))

    def test_follows_a_drop_step(self):
        ground, ledge = PlatformLine(LINES[GROUND]), PlatformLine(LINES[LEDGE])
        mob = Rect("Mob", "red", 80, 560, 120, 600, 1)
        step = navigation.Step("drop", ground, 1000, 1100)
        p = navigation.plan(self.player(950, feet=520), [ground, ledge, mob], 100, router=lambda goal: step)
        self.assertEqual((p.route, p.target), ("down", ground))
        self.assertEqual(p.dx, 1000 + navigation.drop_margin - 950)  # Walks into where the drop lands on the ground

    def test_falls_back_without_a_route(self):  # No recorded way: the local guesses still work
        ground, ledge = PlatformLine(LINES[GROUND]), PlatformLine(LINES[LEDGE])
        mob = Rect("Mob", "red", 980, 480, 1020, 520, 1)
        p = navigation.plan(self.player(800), [ground, ledge, mob], 100, router=lambda goal: None)
        self.assertEqual((p.route, p.target), ("up", ledge))


class RouterTests(unittest.TestCase):  # calculations' router, on the made-up map through a stand-in recorder (map = screen coords)
    def mapper(self, feet):
        platforms = map_recorder.PlatformMap()
        return SimpleNamespace(lines=LINES, ladders=[ROPE], feet=feet, frame_rect=(0, 0, 1366, 768), platforms=platforms,
                               screen_shift=lambda rect: (0, 0))

    def setUp(self):
        self.thread = calculations.CalculationThread()
        patcher = mock.patch.object(values, "nav_jump_height", 100)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_route_to_a_mob_on_the_top(self):
        mob = Rect("Mob", "red", 480, 260, 520, 300, 1)
        with mock.patch.object(values, "planned_route", None):
            step = self.thread.route_step(mob, self.mapper((100, 600)))
            self.assertEqual((step.kind, step.target.name, step.target.center_x), ("rope", "Ladder", 600))
            self.assertEqual(values.planned_route[0], (100, 600))  # Kept for the overlay's Route option
            self.assertEqual(values.planned_route[-1], (600, 300))

    def test_no_route_to_the_next_piece_of_the_same_platform(self):
        lines = [[(0, 600), (500, 600)], [(520, 602), (1000, 602)]]
        mapper = self.mapper((100, 600))
        mapper.lines = lines
        mob = Rect("Mob", "red", 780, 562, 820, 602, 1)
        self.assertIsNone(self.thread.route_step(mob, mapper))  # Just walk there

    def test_no_route_for_a_mob_on_the_same_platform(self):
        mob = Rect("Mob", "red", 280, 560, 320, 600, 1)
        self.assertIsNone(self.thread.route_step(mob, self.mapper((100, 600))))

    def test_exploring_heads_for_where_mobs_were_seen(self):
        mapper = self.mapper((100, 600))
        busy = map_recorder.PlatformMap()
        for x in range(400, 800, 4):  # Mobs often seen on the top
            busy.add_ground(x, 300)
        for x in range(900, 1100, 4):
            busy.add_ground(x, 520)
        busy.see((0, 0, 1366, 768), [(400, 800, 300)], map_recorder.learn_time * 2)  # Watched, with mobs on the top the whole time
        mapper.platforms = busy
        step = self.thread.route_step(None, mapper)
        self.assertEqual(step.kind, "rope")  # The top, not the nearer ledge where no mob was seen
        self.assertEqual(self.thread.explore_goal, TOP)


if __name__ == "__main__":
    unittest.main()
