# Reads HP/MP and EXP from the status bar by matching the game's pixel font

import re
import cv2
import numpy as np
from tools import screen

search_height = 80  # Status bar sits at the bottom of the game area
text_width = 90  # Room for "[99999/99999]" after the label
exp_text_width = 260  # Room after the MP label for its value, the EXP label and "1,234,567[99.99%]"
label_tolerance = 2  # Mismatched pixels allowed when finding a label

# Glyphs of the status bar font, cropped to their visible pixels
FONT = {
    '/': ('..#', '..#', '.#.', '.#.', '#..', '#..'),
    ',': ('.#', '#.'),
    '.': ('#',),
    '%': ('.#....#', '#.#..#.', '.#..#..', '...#...', '..#..#.', '.#..#.#', '#....#.'),
    '0': ('.###.', '#...#', '#...#', '#...#', '#...#', '#...#', '.###.'),
    '1': ('.#', '##', '.#', '.#', '.#', '.#', '.#'),
    '2': ('.###.', '#...#', '....#', '...#.', '..#..', '.#...', '#####'),
    '3': ('.###.', '#...#', '....#', '..##.', '....#', '#...#', '.###.'),
    '4': ('...#.', '..##.', '.#.#.', '#..#.', '#####', '...#.', '...#.'),
    '5': ('#####', '#....', '#....', '.###.', '....#', '#...#', '.###.'),
    '6': ('.###.', '#...#', '#....', '####.', '#...#', '#...#', '.###.'),
    '7': ('#####', '....#', '....#', '....#', '...#.', '..#..', '..#..'),
    '8': ('.###.', '#...#', '#...#', '.###.', '#...#', '#...#', '.###.'),
    '9': ('.###.', '#...#', '#...#', '.####', '....#', '#...#', '.###.'),
    '[': ('##', '#.', '#.', '#.', '#.', '#.', '##'),
    ']': ('##', '.#', '.#', '.#', '.#', '.#', '##'),
}

# Bold labels left of each value; the value text shares their rows
LABELS = {
    'HP': ('###..###.######.', '###..###.###.###', '###..###.##..###', '########.###.###', '########.######.',
           '###..###.####...', '###..###.##.....', '###..###.##.....', '###..###.##.....'),
    'MP': ('####..####.######.', '####..####.###.###', '#####.####.###.###', '##########.###.###', '##########.######.',
           '##########.#####..', '#######.##.###....', '###.###.##.###....', '###.###.##.###....'),
}


def to_mask(rows):
    return np.array([[c == '#' for c in row] for row in rows])


font_masks = {ch: to_mask(rows) for ch, rows in FONT.items()}
label_masks = {name: to_mask(rows).astype(np.float32) for name, rows in LABELS.items()}
value_pattern = re.compile(r'\[(\d+)/(\d+)\]')
exp_pattern = re.compile(r'^\[\d+/\d+\]\D*?(\d[\d,]*)\[(\d+\.\d+)%\]')  # MP's value, the EXP label (unknown glyphs), then EXP


def text_mask(rgb):  # Light text (white labels, yellow values) on the dark bar
    return (rgb[:, :, 0] > 120) & (rgb[:, :, 1] > 120)


def find_label(mask, name):
    label = label_masks[name]
    if mask.shape[0] < label.shape[0] or mask.shape[1] < label.shape[1]:
        return None
    result = cv2.matchTemplate(mask.astype(np.float32), label, cv2.TM_SQDIFF)  # Counts mismatched pixels
    min_val, _, min_loc, _ = cv2.minMaxLoc(result)
    if min_val > label_tolerance:
        return None
    return min_loc


def read_glyphs(mask):  # Splits on blank columns and matches each glyph exactly, '?' if unknown
    text = ''
    cols = mask.any(axis=0)
    x = 0
    while x < len(cols):
        if not cols[x]:
            x += 1
            continue
        start = x
        while x < len(cols) and cols[x]:
            x += 1
        glyph = mask[:, start:x]
        rows = np.flatnonzero(glyph.any(axis=1))
        glyph = glyph[rows[0]:rows[-1] + 1]
        text += next((ch for ch, g in font_masks.items() if g.shape == glyph.shape and (g == glyph).all()), '?')
    return text


def read_value(mask, name):  # Returns (current, max), or None if not readable
    loc = find_label(mask, name)
    if loc is None:
        return None
    x, y = loc
    height, width = label_masks[name].shape
    text = read_glyphs(mask[y:y + height, x + width:x + width + text_width])
    match = value_pattern.search(text)
    if match is None:
        return None
    return int(match[1]), int(match[2])


def read_exp(mask):  # Returns (exp, percent), or None if not readable. Its label is a different font, but it's always right of
    # MP's value on the same rows
    loc = find_label(mask, 'MP')
    if loc is None:
        return None
    x, y = loc
    height, width = label_masks['MP'].shape
    match = exp_pattern.search(read_glyphs(mask[y:y + height, x + width:x + width + exp_text_width]))
    if match is None:
        return None
    return int(match[1].replace(',', '')), float(match[2])


def read_frame(im):  # Reads from an already grabbed frame of the game area; returns (hp, mp, exp): hp and mp each (current, max),
    # exp (exp, percent), any of them None if not readable
    rgb = screen.pixels(im)
    strip = rgb[max(0, rgb.shape[0] - search_height):]
    mask = text_mask(strip)
    return read_value(mask, 'HP'), read_value(mask, 'MP'), read_exp(mask)


def grab(window_rect):  # Just the bottom of the game area, or None if not found
    if window_rect is None:
        return None
    x1, y1, x2, y2 = window_rect
    return screen.grab((x1, max(y1, y2 - search_height), x2, y2))


def read(window_rect):  # Grabs the bottom of the game area itself
    im = grab(window_rect)
    if im is None:
        return None, None, None
    return read_frame(im)


def main():
    import ctypes
    from tools import window_functions
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
    window_functions.maple_name = "MapleStory"
    print(read(window_functions.get_maple_client_rect()))


if __name__ == "__main__":
    main()
