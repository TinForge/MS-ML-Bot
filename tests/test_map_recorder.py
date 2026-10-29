# Tests for calibration and platform recording, using made-up movement in map coords (y grows downwards)

import json
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
        self.assertTrue(c.anchored)  # One sample could be the dot trailing in a fast drop
        for i in range(map_recorder.jump_samples):
            c.add((900 + 5000 + i, 500), minimap_at(900 + i, 500))
        self.assertTrue(c.anchored)  # Still off: a real jump, followed once the new samples outnumber the old
        self.assertAlmostEqual(c.to_map((950 + 5000, 500))[0], 950, delta=6)

    def test_the_dot_trailing_in_a_drop_keeps_the_anchor(self):
        c = Calibration(SCALE)
        for i in range(8):
            c.add((300, 500), minimap_at(300, 500))
        offset = c.offset
        for i in range(12):  # Dropping 22 px a frame, the dot 3 minimap px (30 game px) behind
            y = 500 + 22 * i
            c.add((300, y), minimap_at(300, y - 30))
        for i in range(8):  # Landed: caught up
            c.add((300, 764), minimap_at(300, 764))
        self.assertTrue(c.anchored)
        self.assertAlmostEqual(c.offset[1], offset[1], delta=SCALE)


class RopeTests(unittest.TestCase):
    def test_wandering_readings_make_one_rope(self):  # Climbing readings drift sideways more than a few pixels
        m = PlatformMap()
        for i, y in enumerate(range(600, 300, -4)):
            m.add_ladder(500 + (15 if i % 3 == 0 else -12), y)
        self.assertEqual(len(m.ladders), 1)
        self.assertEqual((m.ladders[0]["top"], m.ladders[0]["bottom"]), (304, 600))

    def test_ropes_at_the_same_x_on_different_floors_stay_apart(self):
        m = PlatformMap()
        for y in range(600, 450, -4):
            m.add_ladder(500, y)
        for y in range(1200, 1000, -4):
            m.add_ladder(510, y)
        self.assertEqual(len(m.ladders), 2)

    def test_ropes_recorded_as_two_are_joined_on_loading(self):  # Recorded side by side before the wider merge
        m = PlatformMap.from_json({"ladders": [{"x": 2920, "top": 1365, "bottom": 1594, "count": 190},
                                               {"x": 2904, "top": 1377, "bottom": 1411, "count": 13},
                                               {"x": 2821, "top": 627, "bottom": 699, "count": 12}]})  # Another floor
        self.assertTrue(m.dirty)  # Saved joined
        ropes = sorted((round(r["x"]), r["top"], r["bottom"], r["count"]) for r in m.ladders)
        self.assertEqual(ropes, [(2821, 627, 699, 12), (2919, 1365, 1594, 203)])

    def test_on_a_rope_is_still_narrow(self):  # Ground beside a rope passing through a platform still records
        m = PlatformMap()
        for y in range(600, 300, -3):
            m.add_ladder(500, y)
        self.assertTrue(m.on_ladder(504, 450))
        self.assertFalse(m.on_ladder(520, 450))


class EraseTests(unittest.TestCase):  # Debug panel's Erase: cleaning up bad recording by going over it
    def recorded(self):
        m = PlatformMap()
        for _ in range(3):
            for x in range(0, 800, 2):
                m.add_ground(x, 600)  # The floor
            for x in range(200, 400, 2):
                m.add_ground(x, 520)  # A platform above it
        for y in range(300, 600, 3):
            m.add_ladder(600, y)  # A rope from the floor up
        m.dirty = False
        return m

    def test_removes_the_ground_walked_over(self):
        m = self.recorded()
        for x in range(500, 700, 6):  # Walking along the floor
            m.erase(x, 600)
        self.assertTrue(m.dirty)
        floor = sorted((float(line[0][0]), float(line[-1][0])) for line in m.platforms() if line[0][1] == 600)
        self.assertEqual(len(floor), 2)  # Split where it was erased: 24 px either side of the feet, from 500 to 698
        self.assertAlmostEqual(floor[0][1], 476, delta=4)
        self.assertAlmostEqual(floor[1][0], 722, delta=4)
        self.assertEqual(len(m.confirmed_ladders()), 1)  # Walked past the rope's foot: kept
        self.assertTrue(any(line[0][1] == 520 for line in m.platforms()))  # 80 px above: kept

    def test_jumping_through_a_scrap_in_mid_air_removes_it(self):
        m = self.recorded()
        for y in range(600, 440, -22):  # Feet passing up through the platform at 520, ~22 px a frame
            m.erase(300, y)
        self.assertEqual([line for line in m.platforms() if line[0][1] == 520 and line[0][0] <= 300 <= line[-1][0]], [])

    def test_removes_a_rope_once_part_way_up_it(self):  # How a rope recorded by a fall is cleaned up: drop through it again
        m = self.recorded()
        m.erase(600, 600)  # At its foot: still there
        self.assertEqual(len(m.ladders), 1)
        m.erase(603, 450)
        self.assertEqual(m.ladders, [])

    def test_nothing_there_changes_nothing(self):
        m = self.recorded()
        m.erase(1500, 100)
        self.assertFalse(m.dirty)


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
        self.player = position  # The dot in the view: where it is doesn't matter here


class SafetyTests(unittest.TestCase):  # Where mobs go on recorded ground, learned while watching
    def recorded(self):  # Ground walked from x 100 to 700 at height 500
        m = PlatformMap()
        for _ in range(2):
            for x in range(100, 700, 2):
                m.add_ground(x, 500)
        return m

    def test_ground_near_mobs_is_busy(self):  # A spot is as unsafe as the busiest ground within a mob's reach of it
        m = self.recorded()
        for _ in range(100):  # 100 s watched; a mob at x 300-340 for 8 s of it
            m.see((0, 0, 1366, 768), [], 0.92)
            m.see((0, 0, 1366, 768), [(300, 340, 500)], 0.08)
        self.assertEqual(m.safety_at(320, 500), map_recorder.BUSY)  # Where it stood: 8% of the time
        self.assertEqual(m.safety_at(390, 500), map_recorder.BUSY)  # Within reach of it
        self.assertEqual(m.safety_at(600, 500), map_recorder.SAFE)  # Out of reach
        runs = m.safety_runs(m.platforms())
        busy = [points for safety, points in runs if safety == map_recorder.BUSY]
        self.assertEqual(len(busy), 1)
        self.assertAlmostEqual(busy[0][0][0], 300 - map_recorder.danger_reach, delta=8)  # Red from reach before it to reach after
        self.assertAlmostEqual(busy[0][-1][0], 340 + map_recorder.danger_reach, delta=8)
        self.assertEqual({s for s, _ in runs}, {map_recorder.SAFE, map_recorder.BUSY})

    def test_not_watched_long_enough_is_unknown(self):
        m = self.recorded()
        m.see((0, 0, 1366, 768), [(300, 340, 500)], map_recorder.learn_time / 2)
        self.assertEqual(m.safety_at(320, 500), map_recorder.UNKNOWN)

    def test_walking_over_again_merges_drifting_heights(self):  # Two readings 7 px apart started two heights; they average together
        m = PlatformMap()
        for x in range(100, 300, 2):
            m.add_ground(x, 500)
        column = m.ground[50]
        column.append([511.0, 1, 0.0, 0.0])  # A second height that started 11 px away
        m.add_ground(201, 506)  # Walking over again: joins the nearest, and the two merge
        self.assertEqual(len(m.ground[50]), 1)
        self.assertEqual(m.ground[50][0][1], sum(1 for x in range(100, 300, 2) if int(x // 4) == 50) + 2)

    def test_older_recordings_tidied_on_load(self):
        loaded = PlatformMap.from_json({"ground": {"50": [[500.0, 5, 1.0, 40.0], [507.0, 3, 2.0, 30.0], [580.0, 4, 0.0, 10.0]]}})
        self.assertEqual(len(loaded.ground[50]), 2)  # 500 and 507 merged; 580 is another platform
        merged = loaded.ground[50][0]
        self.assertAlmostEqual(merged[0], (500 * 5 + 507 * 3) / 8)
        self.assertEqual((merged[1], merged[2], merged[3]), (8, 3.0, 40.0))  # Stood on added, mob time added, watched kept
        self.assertTrue(loaded.dirty)  # Saved tidied

    def test_ground_recorded_twice_is_one_platform(self):  # Readings a little below the platform (landings) along part of it
        m = PlatformMap()
        for _ in range(3):
            for x in range(100, 500, 2):
                m.add_ground(x, 500)
            for x in range(300, 380, 2):
                m.add_ground(x, 518)  # 18 px below: beyond merging in a column, but lying along the platform
        self.assertEqual(len(m.platforms()), 1)

    def test_stair_steps_stay_separate(self):  # Steps touch only at their ends, each a jump higher
        m = PlatformMap()
        for _ in range(3):
            for i, height in enumerate((600, 570, 540)):
                for x in range(100 + i * 100, 200 + i * 100, 2):
                    m.add_ground(x, height)
        self.assertEqual(sorted(round(line[0][1]) for line in m.platforms()), [540, 570, 600])

    def test_slivers_are_not_platforms(self):  # A few columns of "ground" are readings taken while hanging on a rope
        m = PlatformMap()
        for _ in range(10):
            m.add_ground(500, 400)
            m.add_ground(503, 400)
        self.assertEqual(m.platforms(), [])
        for x in range(100, 300, 2):
            m.add_ground(x, 600)
        self.assertEqual(len(m.platforms()), 1)

    def test_no_ground_part_way_up_a_rope(self):
        m = PlatformMap()
        for y in range(400, 600, 5):
            m.add_ladder(500, y)
        self.assertTrue(m.on_ladder(502, 480))
        self.assertFalse(m.on_ladder(502, 598))  # Its foot, on the ground
        self.assertFalse(m.on_ladder(560, 480))  # Beside it

    def test_judges_each_stretch_once_watched_long_enough(self):
        m = self.recorded()
        view, mob = (0, 0, 1000, 800), (560, 600, 498)  # A mob standing around x 560-600
        for _ in range(20):  # 20 s with the mob there
            m.see(view, [mob], 1.0)
        self.assertEqual(m.safety_at(580, 500), map_recorder.UNKNOWN)  # Not watched for learn_time yet
        for _ in range(20):
            m.see(view, [], 1.0)
        self.assertEqual(m.safety_at(580, 500), map_recorder.BUSY)  # Mobs there half the time
        self.assertEqual(m.safety_at(200, 500), map_recorder.SAFE)
        runs = m.safety_runs(m.platforms())
        self.assertEqual([safety for safety, _ in runs], [map_recorder.SAFE, map_recorder.BUSY, map_recorder.SAFE])
        self.assertEqual(runs[0][1][-1], runs[1][1][0])  # Runs meet, so the line is drawn without gaps

    def test_mobs_never_add_ground(self):  # Only platforms the player has walked learn anything
        m = self.recorded()
        before = m.platforms()
        for _ in range(40):
            m.see((0, 0, 1000, 800), [(800, 840, 300), (300, 340, 400)], 1.0)  # Off the recorded ground, and above it
        self.assertEqual(m.platforms(), before)
        self.assertEqual(m.safety_at(820, 300), map_recorder.UNKNOWN)
        self.assertEqual(m.safety_at(320, 500), map_recorder.SAFE)  # The mob at height 400 wasn't standing on it

    def test_only_ground_on_screen_is_watched(self):
        m = self.recorded()
        for _ in range(40):
            m.see((0, 0, 400, 800), [], 1.0)
        self.assertEqual((m.safety_at(200, 500), m.safety_at(600, 500)), (map_recorder.SAFE, map_recorder.UNKNOWN))

    def test_saved_and_reloaded_with_older_files(self):
        m = self.recorded()
        m.see((0, 0, 1000, 800), [(560, 600, 498)], 40.0)
        again = PlatformMap.from_json(json.loads(json.dumps(m.to_json())))
        self.assertEqual(again.safety_at(580, 500), map_recorder.BUSY)
        old = PlatformMap.from_json({"ground": {"30": [[500.0, 3]]}})  # Saved before mob statistics existed
        self.assertEqual(old.safety_at(122, 500), map_recorder.UNKNOWN)


class MapperTests(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.object(map_recorder, "folder", tempfile.mkdtemp())
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_startup_status(self):  # What the Debug panel shows until it's lined up with the map
        mapper = Mapper()
        mapper.switch("test")
        mapper.camera = FakeCamera()
        frame_rect, player = (0, 0, 1366, 768), (658, 334, 708, 400)
        mapper.update(None, frame_rect, None, FakeMinimap((50, 50)), 0.0, True)
        self.assertEqual(mapper.status, "player not found")
        mapper.update(None, frame_rect, player, FakeMinimap(None), 0.1, True)
        self.assertEqual(mapper.status, "minimap dot not found")
        for i in range(10):  # Climbing: the dot moves 5 minimap px
            mapper.camera.position = (0, -i * 5)
            mapper.update(None, frame_rect, player, FakeMinimap((50, 50 - i * 0.5)), 0.2 + i / 30, True)
        self.assertIn("dot moved 4 of 12 px, 10 of 40 readings", mapper.status)
        for i in range(10, 60):  # On up the rope
            mapper.camera.position = (0, -i * 5)
            mapper.update(None, frame_rect, player, FakeMinimap((50, 50 - i * 0.5)), 0.2 + i / 30, True)
        self.assertIsNone(mapper.status)  # Lined up: the panel shows the platform count
        self.assertAlmostEqual(mapper.calibration.scale, 10, delta=0.5)  # Measured from going up alone

    def test_walking_off_a_ledge_records_nothing_past_it(self):  # The first frames of the fall still look like walking
        for rate in (18, 30):
            mapper = Mapper()
            mapper.switch("test")
            mapper.camera = FakeCamera()
            mapper.calibration.scale, frame_rect = SCALE, (0, 0, 1366, 768)
            for lap in range(3):  # Walk right along the platform at 125 px/s and off its end at 500, falling to the floor at 700
                for i in range(int(rate * 3.6)):
                    t = lap * 10 + i / rate
                    x = 200 + 125 * i / rate
                    fall = max(0.0, (x - 500) / 125)
                    y = min(500 + 2000 * fall * fall / 2, 700)
                    mapper.camera.position = (x - 683, y - 400)
                    player_rect = (683 - 25, 400 - 66, 683 + 25, 400)
                    mapper.update(None, frame_rect, player_rect, FakeMinimap(minimap_at(x, y)), t, record=True)
            ledge = [line for line in mapper.platforms.platforms() if abs(line[0][1] - 500) < 10]
            self.assertEqual(len(ledge), 1)
            self.assertLessEqual(ledge[0][-1][0], 500 + map_recorder.bin_size, rate)  # Ends at the ledge
            self.assertGreater(ledge[0][-1][0], 500 - 30, rate)  # Only a little short of it: what was held when it fell
            self.assertTrue(all(abs(y - 500) < 2 for _, y in ledge[0]), rate)  # Not sagging into the fall

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

        found = mapper.screen_rects()  # The same platforms and ladder, in screen coords for navigation
        ground_x, ground_y = mapper.to_screen((400, 600), frame_rect)
        under = [r for r in found if r.name == "Platform" and r.x1 <= ground_x <= r.x2 and abs(r.top_at(ground_x) - ground_y) < 6]
        self.assertEqual(len(under), 1)
        ladder_x = mapper.to_screen((600, 500), frame_rect)[0]
        self.assertEqual([round(abs(r.center_x - ladder_x) / 10) for r in found if r.name == "Ladder"], [0])

    def test_draws_ahead_of_the_scrolling_camera(self):  # Frames are 40-70 ms old when drawn: map drawings go where the screen is now
        mapper = Mapper()
        mapper.switch("test")
        mapper.calibration.offset, frame_rect = (0.0, 0.0), (0, 0, 1366, 768)
        for i in range(10):  # The camera scrolls right at 150 px/s, 30 frames a second
            mapper.track_scroll((5.0, 0.0), 10.0 + i / 30)
        mapper.camera.position = (300.0, 0.0)
        grabbed = 10.0 + 9 / 30
        self.assertEqual(mapper.to_screen((500, 600), frame_rect), (200.0, 600.0))  # As of the frame
        x, y = mapper.to_screen((500, 600), frame_rect, grabbed + 0.06)
        self.assertAlmostEqual(x, 200 - 150 * 0.06, delta=0.5)  # 9 px further left: the scene moves against the camera
        self.assertEqual(y, 600)
        x, _ = mapper.to_screen((500, 600), frame_rect, grabbed + 5)  # Frames stopped coming: not guessed on and on
        self.assertAlmostEqual(x, 200 - 150 * map_recorder.max_predict, delta=0.5)

    def test_not_drawn_ahead_when_the_camera_is_lost(self):
        mapper = Mapper()
        mapper.switch("test")
        mapper.calibration.offset = (0.0, 0.0)
        mapper.track_scroll((5.0, 0.0), 10.0)
        mapper.track_scroll((5.0, 0.0), 10.033)
        mapper.track_scroll(None, 10.066)  # Couldn't measure the scroll
        frame_rect = (0, 0, 1366, 768)
        self.assertEqual(mapper.to_screen((500, 600), frame_rect, 10.1), mapper.to_screen((500, 600), frame_rect))

    def test_no_screen_rects_until_anchored(self):
        mapper = Mapper()
        self.assertEqual(mapper.screen_rects(), [])
        mapper.switch("test")
        self.assertEqual(mapper.screen_rects(), [])

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
