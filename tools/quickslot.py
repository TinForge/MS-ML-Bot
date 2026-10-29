# Reads the quickslot panel above the status bar: how many of the item on each key are left, from the count drawn in each slot's
# bottom-left corner, so running out of potions can be told. When the last one is used the item stays, showing 0

import re

import numpy as np

from tools import screen

panel_size = (150, 77)
panel_offset = (431, 144)  # From the game area's bottom-right corner to the panel's top-left (at 1366x768)
SLOTS = {"Shift": (0, 0), "Insert": (0, 1), "Home": (0, 2), "Page Up": (0, 3),  # Key: (row, column). The panel shows what these
         "Ctrl": (1, 0), "Delete": (1, 1), "End": (1, 2), "Page Down": (1, 3)}  # eight keys are bound to
slot_pitch = (35, 34)  # Pixels between slots across and down
empty_share = 0.7  # Share of plain slot background below the key label above which a slot is empty (empty ~0.87, items under 0.4)
max_speck = 2  # Pixels in a column, matching no digit, that are taken for an icon's speck and skipped: an icon's white next to its own
# outline can pass for a stroke, often along the top row, touching a digit

# The count font: 9 rows tall, 1 px white-to-blue strokes outlined in black. Each row has its own exact colour
GRADIENT = np.array([(255, 255, 255)] * 4 + [(0xee, 0xff, 0xff), (0xdd, 0xee, 0xff), (0xbb, 0xdd, 0xff), (0xaa, 0xcc, 0xff), (0x99, 0xcc, 0xff)])
# Digits as found in lossless captures: a stroke pixel needs black on both sides (left and right, or above and below), which leaves
# out where strokes meet. python -m tools.quickslot prints any shape that isn't one of these
FONT = {
    '0': ('.####.', '#....#', '#....#', '#....#', '#....#', '#....#', '#....#', '#....#', '.####.'),
    '1': ('..#', '##.', '..#', '..#', '..#', '..#', '..#', '..#', '..#'),
    '2': ('.####.', '#....#', '.....#', '.....#', '....#.', '..##..', '.#....', '#.....', '.#####'),
    '3': ('.####.', '#....#', '.....#', '.....#', '..###.', '.....#', '.....#', '#....#', '.####.'),
    '4': ('....#.', '...#..', '..#.#.', '.#..#.', '#...#.', '.###.#', '....#.', '....#.', '....#.'),
    '5': ('.#####', '#.....', '#.....', '.####.', '.....#', '.....#', '.....#', '#....#', '.####.'),
    '6': ('..###.', '.#....', '#.....', '.####.', '#....#', '#....#', '#....#', '#....#', '.####.'),
    '7': ('#####.', '.....#', '....#.', '....#.', '...#..', '...#..', '..#...', '..#...', '.#....'),
    '8': ('.####.', '#....#', '#....#', '#....#', '.####.', '#....#', '#....#', '#....#', '.####.'),
    '9': ('.####.', '#....#', '#....#', '#....#', '#....#', '.####.', '.....#', '.....#', '.####.'),
}
font_masks = {ch: np.array([[c == '#' for c in row] for row in rows]) for ch, rows in FONT.items()}
widest_first = sorted(font_masks.items(), key=lambda item: -item[1].shape[1])


def find_panel(rgb):  # The panel from a frame of the game area, or None when it isn't there (hidden with the Short Cut button)
    h, w = rgb.shape[:2]
    x, y = w - panel_offset[0], h - panel_offset[1]
    if x < 0 or y < 0:
        return None
    panel = rgb[y:y + panel_size[1], x:x + panel_size[0]]
    gaps = np.concatenate([panel[top:top + 24, gx:gx + 3] for top in (8, 42) for gx in (37, 72, 107)])  # Dark gaps between slots
    border = panel[5:70, 0]  # Light outer edge
    if (gaps.max(axis=2) < 70).mean() < 0.95 or (border.min(axis=1) > 200).mean() < 0.95:
        return None
    return panel


def slot_origin(row, col):
    return 7 + slot_pitch[0] * col, 6 + slot_pitch[1] * row


def is_empty(panel, row, col):
    x, y = slot_origin(row, col)
    inner = panel[y + 12:y + 28, x + 2:x + 26].astype(int)
    plain = (inner.min(axis=2) >= 200) & (inner.max(axis=2) - inner.min(axis=2) <= 20)  # The slot's light grey
    return plain.mean() > empty_share


def count_mask(panel, row, col):  # The count's stroke pixels, 9 rows from the slot's left edge
    x, y = slot_origin(row, col)
    band = panel[y + 20:y + 29, x - 1:x + 27].astype(int)
    stroke = np.abs(band - GRADIENT[:, None, :]).max(axis=2) <= 2  # Exact in a lossless capture; the slot background is 7 off white
    black = np.pad(band.max(axis=2) < 60, 1, constant_values=True)
    outlined = (black[:-2, 1:-1] & black[2:, 1:-1]) | (black[1:-1, :-2] & black[1:-1, 2:])
    return stroke & outlined


def read_text(mask):  # The digits left to right, each matched where it starts (specks touching one would merge it with the next if
    # split at blank columns), '?' for a shape that isn't a known digit
    text, x, width = "", 0, mask.shape[1]
    while x < width:
        column = mask[:, x]
        if not column.any():
            x += 1
            continue
        ch = next((ch for ch, g in widest_first if x + g.shape[1] <= width and (mask[:, x:x + g.shape[1]] == g).all()), None)
        if ch is not None:
            text += ch
            x += font_masks[ch].shape[1]
        elif column.sum() <= max_speck:
            x += 1
        else:
            text += '?'
            while x < width and mask[:, x].any():
                x += 1
    return text


def slot_count(panel, row, col):  # The count, 0 once they're used up; None for an empty slot, or a count that can't be read
    if is_empty(panel, row, col):
        return None
    text = read_text(count_mask(panel, row, col))
    return int(text) if re.fullmatch(r"\d+", text) else None


def read_frame(im):  # {key: count} for every slot (see slot_count), or None when the panel isn't showing
    panel = find_panel(screen.pixels(im))
    if panel is None:
        return None
    return {key: slot_count(panel, *slot) for key, slot in SLOTS.items()}


def main():  # Reads the game's quickslot and prints each slot's count, with the digits that aren't known yet as text
    import ctypes
    from tools import window_functions
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    window_functions.maple_name = "MapleStory"
    rect = window_functions.get_maple_client_rect()
    panel = find_panel(screen.pixels(screen.grab(rect))) if rect is not None else None
    if panel is None:
        print("Quickslot panel not found")
        return
    for key, slot in SLOTS.items():
        mask = count_mask(panel, *slot)
        text = read_text(mask)
        print(key, slot_count(panel, *slot), text)
        if '?' in text:
            print("   ", tuple("".join("#" if v else "." for v in r) for r in mask))


if __name__ == "__main__":
    main()
