# Tests for stitching the scrolling minimap, using views cut from a larger image at known offsets

import os
import tempfile
import unittest
from unittest import mock

import numpy as np
from PIL import Image

from tools import minimap, minimap_mosaic

fixtures = os.path.join(os.path.dirname(__file__), "fixtures")
ART = np.asarray(Image.open(os.path.join(fixtures, "minimap perion.png")).convert("RGB"))  # Stands in for a full minimap
VIEW = (90, 150)  # View height, width
DOT = (200, 120)  # Player dot centre in ART coords; it stays there while the view scrolls
SPRITE = np.asarray(Image.open("resources/minimap player.png"))


def view_at(x, y, red_at=None):  # The minimap showing ART from (x, y), with the player dot and maybe another player's dot drawn on
    view = ART[y:y + VIEW[0], x:x + VIEW[1]].copy()
    sx, sy = DOT[0] - x - 3, DOT[1] - y - 3  # The 8x8 sprite's centre is 3.5 px in
    if 0 <= sx and 0 <= sy and sx + 8 <= VIEW[1] and sy + 8 <= VIEW[0]:
        alpha = SPRITE[:, :, 3:] > 0
        view[sy:sy + 8, sx:sx + 8] = np.where(alpha, SPRITE[:, :, :3], view[sy:sy + 8, sx:sx + 8])
    if red_at is not None:
        rx, ry = red_at
        view[ry - 2:ry + 3, rx - 2:rx + 3] = (240, 20, 20)
    player = minimap.find_player(view)
    return minimap.Minimap((0, 0, VIEW[1], VIEW[0]), player, map_id="test", area=view, markers=minimap.marker_mask(view, player))


class MosaicTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        patcher = mock.patch.object(minimap_mosaic, "folder", self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)

    def track(self, offsets, tracker=None, red=False):
        tracker = tracker or minimap_mosaic.Tracker()
        positions = []
        for i, (x, y) in enumerate(offsets):
            m = view_at(x, y, red_at=(20 + i * 7, 30) if red else None)
            tracker.update(m)
            positions.append(m.position)
        return tracker, positions

    def test_dot_position_stays_put_while_scrolling(self):
        offsets = [(100, 60), (104, 60), (110, 63), (118, 66), (125, 70), (131, 72)]
        _, positions = self.track(offsets, red=True)  # Another player walking across the view must not disturb it
        self.assertEqual(set(positions), {(DOT[0] - 100 + 0.5, DOT[1] - 60 + 0.5)})  # Same as in the first view

    def test_see_through_background_changing(self):  # The game shows through the minimap, so part of each view keeps changing
        rng = np.random.default_rng(1)
        background = rng.random(ART.shape[:2]) < 0.4  # 40% of the art is "see-through"
        tracker = minimap_mosaic.Tracker()
        positions = []
        for i, (x, y) in enumerate([(100, 60), (100, 60), (104, 61), (110, 63), (110, 63), (118, 66), (125, 70)]):
            m = view_at(x, y)
            noise = rng.integers(0, 255, m.area.shape, dtype=np.uint8)
            see_through = background[y:y + VIEW[0], x:x + VIEW[1]] & ~m.markers
            m.area[see_through] = noise[see_through]  # Different game scenery behind it every time
            tracker.update(m)
            positions.append(m.position)
        self.assertEqual(set(positions), {(DOT[0] - 100 + 0.5, DOT[1] - 60 + 0.5)})

    def test_scrolling_left_and_up_past_the_first_view(self):
        offsets = [(130, 80), (120, 72), (108, 64), (95, 55), (90, 50)]
        tracker, positions = self.track(offsets)
        self.assertEqual(len(set(positions)), 1)
        self.assertEqual(tracker.mosaic.origin, (40, 30))  # Grew 40 px left and 30 px up

    def test_saved_and_reloaded(self):
        tracker, before = self.track([(100, 60), (110, 60), (120, 64)])
        tracker.save()
        self.assertTrue(os.path.exists(os.path.join(self.folder, "test", "minimap.png")))
        _, after = self.track([(115, 62)])  # A fresh tracker loads the saved picture
        self.assertEqual(after[0], before[0])

    def test_jump_to_unseen_area_waits_for_overlap(self):
        tracker, _ = self.track([(100, 60), (105, 60)])
        jumped = view_at(10, 140)  # Nothing in common with what was seen; dot not in view either
        tracker.update(jumped)
        self.assertIsNone(jumped.position)
        _, positions = self.track([(110, 62)], tracker)
        self.assertEqual(positions[0], (DOT[0] - 100 + 0.5, DOT[1] - 60 + 0.5))

    def test_map_change_switches_picture(self):
        tracker, _ = self.track([(100, 60)])
        other = view_at(10, 10)
        other.map_id = "other map"
        tracker.update(other)
        self.assertEqual(tracker.mosaic.map_id, "other map")
        self.assertTrue(os.path.exists(os.path.join(self.folder, "test", "minimap.png")))  # The first map was saved on leaving


if __name__ == "__main__":
    unittest.main()
