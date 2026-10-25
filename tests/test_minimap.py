# Tests for the minimap reader, on minimap crops from real game frames

import os
import unittest

from PIL import Image, ImageDraw

from tools import minimap

fixtures = os.path.join(os.path.dirname(__file__), "fixtures")


def load(name):
    return Image.open(os.path.join(fixtures, name + ".png")).convert("RGB")


class MinimapTests(unittest.TestCase):
    def test_perion(self):
        m, title = minimap.read(load("minimap perion"))
        self.assertEqual(title, (13, 11))
        self.assertEqual(m.map_rect, (15, 78, 219, 190))
        self.assertEqual(m.player, (144.5, 49.5))  # Not fooled by the yellow sand in the map art
        self.assertGreater(len(m.others), 5)

    def test_ellinia(self):
        m, _ = minimap.read(load("minimap ellinia"))
        self.assertEqual(m.map_rect, (15, 78, 222, 190))  # Window width differs per map
        self.assertEqual(m.player, (99.5, 49.5))

    def test_maps_have_distinct_stable_ids(self):
        perion, _ = minimap.read(load("minimap perion"))
        ellinia, _ = minimap.read(load("minimap ellinia"))
        self.assertNotEqual(perion.map_id, ellinia.map_id)
        self.assertEqual(perion.map_id, minimap.read(load("minimap perion"))[0].map_id)

    def test_finds_moved_window(self):
        im = load("minimap ellinia")
        moved = Image.new("RGB", (700, 500), (40, 90, 40))
        moved.paste(im, (250, 180))
        m, title = minimap.read(moved, last_title=(13, 11))  # Not where it was last time: falls back to a full search
        self.assertEqual(title, (263, 191))
        self.assertEqual(m.map_rect, (265, 258, 472, 370))
        self.assertEqual(m.player, (99.5, 49.5))  # Dot is relative to the map area

    def test_missing_and_hidden_dot(self):
        self.assertEqual(minimap.read(Image.new("RGB", (400, 300), (40, 90, 40))), (None, None))
        im = load("minimap perion")
        ImageDraw.Draw(im).rectangle((15 + 140, 78 + 45, 15 + 150, 78 + 55), fill=(60, 60, 60))  # Cover the dot
        self.assertIsNone(minimap.read(im)[0].player)


if __name__ == "__main__":
    unittest.main()
