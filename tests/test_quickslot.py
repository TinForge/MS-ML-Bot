# Tests for reading the quickslot panel, on a made-up panel drawn with its layout and count font (real captures are game art, kept
# out of the repository)

import unittest
from unittest import mock

import numpy as np

from data import values
from process import bot
from tools import keyboard, quickslot

SLOT_GREY, ICON = (0xe2, 0xe3, 0xe5), (0xff, 0x99, 0x00)
UNKNOWN = np.array([[c == '#' for c in row] for row in ('######', '#....#', '#....#', '######', '#....#', '#....#', '#....#', '#....#', '#....#')])


def game_area(counts, width=1366, height=768):  # A game area with the panel in its place; counts: {key: None for empty, or text}
    frame = np.full((height, width, 3), 90, np.uint8)
    w, h = quickslot.panel_size
    panel = np.full((h, w, 3), 40, np.uint8)  # Dark: the gaps between slots
    panel[:, 0] = 230  # Light outer edge
    for key, (row, col) in quickslot.SLOTS.items():
        x, y = quickslot.slot_origin(row, col)
        text = counts.get(key)
        panel[y:y + 30, x:x + 28] = SLOT_GREY if text is None else ICON
        if text:
            draw(panel, x, y + 20, text)
    frame[height - quickslot.panel_offset[1]:height - quickslot.panel_offset[1] + h, width - quickslot.panel_offset[0]:width - quickslot.panel_offset[0] + w] = panel
    return frame


def draw(panel, x, y, text):  # The count as the game draws it: strokes in the row's colour on black
    for ch in text:
        glyph = quickslot.font_masks.get(ch, UNKNOWN)  # Not a digit: an 'A'
        h, w = glyph.shape
        panel[y - 1:y + h + 1, x - 1:x + w + 1] = 0
        for r, c in zip(*np.nonzero(glyph)):
            panel[y + r, x + c] = quickslot.GRADIENT[r]
        x += w + 1


class QuickslotTests(unittest.TestCase):
    def test_reads_counts(self):
        frame = game_area({"Delete": "45", "End": "1230", "Page Down": "1", "Insert": "6789"})
        counts = quickslot.read_frame(frame)
        self.assertEqual([counts[k] for k in ("Delete", "End", "Page Down", "Insert")], [45, 1230, 1, 6789])

    def test_used_up_reads_zero(self):  # The item stays on the key, showing 0
        self.assertEqual(quickslot.read_frame(game_area({"End": "0"}))["End"], 0)

    def test_empty_slot_or_unreadable_count_is_unknown(self):
        counts = quickslot.read_frame(game_area({"End": "4A", "Ctrl": "", "Home": None}))  # Not a digit; a skill, with no count; nothing
        self.assertEqual((counts["End"], counts["Ctrl"], counts["Home"]), (None, None, None))

    def test_specks_touching_the_digits_are_skipped(self):  # An icon's white beside its own outline can pass for a stroke
        frame = game_area({"Home": ""})
        x, y = quickslot.slot_origin(*quickslot.SLOTS["Home"])
        ox, oy = 1366 - quickslot.panel_offset[0], 768 - quickslot.panel_offset[1]
        panel = frame[oy:oy + quickslot.panel_size[1], ox:ox + quickslot.panel_size[0]]
        draw(panel, x, y + 20, "3")
        draw(panel, x + 8, y + 20, "0")  # 2 px apart, as in the game
        panel[y + 20, x + 6:x + 8] = 255  # Two white pixels between them on the top row, black above and below: they pass for a stroke
        self.assertEqual(quickslot.read_frame(frame)["Home"], 30)

    def test_hidden_panel(self):  # Folded away with the Short Cut button
        self.assertIsNone(quickslot.read_frame(np.full((768, 1366, 3), 90, np.uint8)))

    def test_counts_found_on_any_icon(self):  # Only the exact stroke colours count: an icon's near-white pixels don't
        frame = game_area({"End": "10"})
        x, y = quickslot.slot_origin(*quickslot.SLOTS["End"])
        ox, oy = 1366 - quickslot.panel_offset[0], 768 - quickslot.panel_offset[1]
        frame[oy + y + 20:oy + y + 24, ox + x + 14:ox + x + 20] = (0xf8, 0xf9, 0xfa)  # Off-white beside the digits
        self.assertEqual(quickslot.read_frame(frame)["End"], 10)


class AutoPotionTests(unittest.TestCase):  # Out of potions: pressing the key does nothing
    def test_no_press_when_out(self):
        thread = bot.BotThread()
        with mock.patch.object(values, "quickslot", {"Delete": 0}), mock.patch.object(keyboard, "PressKey") as press, \
                mock.patch.object(keyboard, "ReleaseKey"), mock.patch.object(bot, "potion_confirm_reads", 1):
            thread.use_potion("HP", (10, 100), 50, "Delete")
            self.assertFalse(press.called)
            values.quickslot = {"Delete": 12}
            thread.use_potion("HP", (10, 100), 50, "Delete")
            self.assertTrue(press.called)

    def test_potions_left(self):
        with mock.patch.object(values, "quickslot", None):
            self.assertIsNone(bot.potions_left("End"))
        with mock.patch.object(values, "quickslot", {"End": 7}):
            self.assertEqual(bot.potions_left("End"), 7)


if __name__ == "__main__":
    unittest.main()
