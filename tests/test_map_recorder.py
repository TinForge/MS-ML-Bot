# Tests for calibration and platform recording, using made-up movement in map coords (y grows downwards)

import tempfile
import unittest
from unittest import mock

from tools import map_recorder
from tools.map_recorder import Calibration, Mapper, PlatformMap

SCALE = 10.0  # Game pixels per minimap pixel in these tests


def minimap_at(x, y):  # Minimap dot position for a map position: coarse, in half-pixel steps like real dot centres
    return round(x / SCALE * 2) / 2, round(y / SCALE * 2) / 2


class CalibrationTests(unittest.TestCase):
    def test_measures_scale_and_ties_to_map(self):
        c = Calibration()
        offset = (1234.0, -321.0)  # Camera coords start wherever the session started
        for i in range(80):
            x, y = 300 + i * 4, 500 + (i % 20) * 3
            c.add((x + offset[0], y + offset[1]), minimap_at(x, y))
        self.assertAlmostEqual(c.scale, SCALE, delta=SCALE * 0.03)
        mx, my = c.to_map((700 + offset[0], 520 + offset[1]))
        self.assertAlmostEqual(mx, 700, delta=6)
        self.assertAlmostEqual(my, 520, delta=6)

    def test_saved_scale_anchors_quickly_and_reanchors_after_a_jump(self):
        c = Calibration(SCALE)
        for i in range(8):
            c.add((300 + i * 4, 500), minimap_at(300 + i * 4, 500))
        self.assertTrue(c.anchored)
        c.add((900 + 5000, 500), minimap_at(900, 500))  # Camera coords jumped by 5000
        self.assertFalse(c.anchored)


class PlatformMapTests(unittest.TestCase):
    def walk(self, m, x1, x2, y=lambda x: 500, times=2):
        for _ in range(times):
            for x in range(x1, x2, 2):
                m.add_ground(x, y(x))

    def test_flat_platform(self):
        m = PlatformMap()
        self.walk(m, 100, 300)
        lines = m.platforms()
        self.assertEqual(len(lines), 1)
        (x1, y1), (x2, y2) = lines[0][0], lines[0][-1]
        self.assertLess(x1, 105)
        self.assertGreater(x2, 295)
        self.assertEqual((round(y1), round(y2)), (500, 500))

    def test_slope_kept_as_a_slanted_line(self):
        m = PlatformMap()
        self.walk(m, 100, 300, y=lambda x: 500 - (x - 100) * 0.5)  # Rises 100 px over 200
        line = m.platforms()[0]
        self.assertAlmostEqual(line[0][1] - line[-1][1], 100, delta=6)

    def test_stacked_platforms_and_gaps_stay_separate(self):
        m = PlatformMap()
        self.walk(m, 100, 300, y=lambda x: 500)
        self.walk(m, 150, 250, y=lambda x: 420)  # Above, over the same columns
        self.walk(m, 400, 500, y=lambda x: 500)  # Same height, across a 100 px gap
        self.assertEqual(len(m.platforms()), 3)

    def test_one_walk_is_enough_but_stray_readings_are_ignored(self):
        m = PlatformMap()
        for x in range(100, 300, 8):  # One pass at walking pace: about one sample every other column
            m.add_ground(x, 500)
        m.add_ground(600, 300)  # A stray reading somewhere else
        m.add_ground(605, 302)
        lines = m.platforms()
        self.assertEqual(len(lines), 1)
        self.assertLess(lines[0][0][0], 110)

    def test_ladder(self):
        m = PlatformMap()
        for _ in range(2):
            for y in range(500, 380, -5):
                m.add_ladder(250 + (y % 3), y)
        ladders = m.confirmed_ladders()
        self.assertEqual(len(ladders), 1)
        self.assertEqual((round(ladders[0]["x"]), ladders[0]["top"], ladders[0]["bottom"]), (251, 385, 500))

    def test_json_round_trip(self):
        m = PlatformMap()
        self.walk(m, 100, 300)
        m.add_ladder(250, 400)
        self.assertEqual(PlatformMap.from_json(m.to_json()).platforms(), m.platforms())


class FakeCamera:  # Stands in for CameraTracker: the camera follows the player
    def __init__(self):
        self.position = (0.0, 0.0)
        self.lost = False

    def update(self, frame):
        pass

    def reset(self):
        pass


class FakeMinimap:
    def __init__(self, position):
        self.map_id = "test"
        self.position = position


class MapperTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(map_recorder, "folder", tempfile.mkdtemp())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_records_walked_platforms_and_climbed_ladder(self):
        mapper = Mapper()
        mapper.switch("test")
        mapper.camera = FakeCamera()
        frame_rect = (100, 50, 1466, 818)
        t = 0.0

        def step(x, y):  # Player feet at map (x, y); the camera keeps them near the screen centre
            nonlocal t
            mapper.camera.position = (x - 683 + 2000, y - 500 - 700)  # Camera coords are offset from map coords
            screen_x, screen_y = x - mapper.camera.position[0] + 2000 + frame_rect[0], y - mapper.camera.position[1] - 700 + frame_rect[1]
            player_rect = (screen_x - 25, screen_y - 66, screen_x + 25, screen_y)
            mapper.update(None, frame_rect, player_rect, FakeMinimap(minimap_at(x, y)), t, record=True)
            t += 1 / 18

        for _ in range(2):  # Walk right along the ground, climb a rope, walk along the upper platform
            for x in range(200, 600, 7):
                step(x, 600)
            for y in range(600, 450, -6):
                step(600, y)
            for x in range(600, 800, 7):
                step(x, 450)
            for y in range(450, 600, 6):  # Back down the rope to repeat
                step(600, y)
        self.assertAlmostEqual(mapper.calibration.scale, SCALE, delta=SCALE * 0.05)
        heights = sorted(round(sum(p[1] for p in line) / len(line)) for line in mapper.platforms.platforms() if len(line) >= 2 and line[-1][0] - line[0][0] > 100)
        self.assertEqual(len(heights), 2)
        self.assertAlmostEqual(heights[0], 450, delta=6)
        self.assertAlmostEqual(heights[1], 600, delta=6)
        ladders = mapper.platforms.confirmed_ladders()
        self.assertEqual(len(ladders), 1)
        self.assertAlmostEqual(ladders[0]["x"], 600, delta=6)
        point = mapper.to_screen((600, 600), frame_rect)  # Drawing maps back onto the screen where the player is
        self.assertIsNotNone(point)

    def test_saved_and_reloaded(self):
        mapper = Mapper()
        mapper.switch("test")
        mapper.calibration.scale = SCALE
        for _ in range(2):
            for x in range(100, 300, 2):
                mapper.platforms.add_ground(x, 500)
        mapper.save()
        again = Mapper()
        again.switch("test")
        self.assertEqual(again.calibration.scale, SCALE)
        self.assertEqual(again.platforms.platforms(), mapper.platforms.platforms())


if __name__ == "__main__":
    unittest.main()
