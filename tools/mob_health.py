# Reads the health bars the game draws above mobs that have been hit. A mob killed in one hit never shows one,
# and the bar disappears the moment the mob dies, so "no bar" means either untouched or dead.
#
# A bar is a white frame 50 px wide with its top and bottom lines 7 rows apart; green fills the health left from the
# left, red shows what was just lost. Bars of bunched-up mobs overlap, so only part of a frame needs to be visible.

from dataclasses import dataclass

import numpy as np

bar_width = 50  # Outer width of a bar, the same for every mob
bar_height = 7  # Rows from the top white line to the bottom one
fill_row = 3  # Row below the top line, through the middle of the fill
fill_start, fill_length = 3, 44  # Where the fill starts after the left edge, and its length at full health
min_line = 20  # Visible length of the top and bottom lines needed to count as a bar
search_above, search_below = 45, 10  # Where a bar's bottom line may be, relative to the top of its mob's box
max_offset = 25  # How far a bar's centre may be from its mob's centre


@dataclass
class Bar:
    x: int  # Left edge in screen coords
    y: int  # Top line in screen coords
    health: float  # Share of health left, 0-1 (a lower bound when the bar is partly covered)
    covered: bool  # Something covers the bar where the fill ends, so the health may be higher

    @property
    def center_x(self):
        return self.x + bar_width / 2


def colours(rgb):  # Masks of the bar's colours; screenshots are JPEG-like, so with some slack
    rgb = rgb.astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    white = rgb.min(axis=2) > 190
    dark = rgb.max(axis=2) < 80
    green = (g > 120) & (g - r > 40) & (g - b > 40)
    red = (r > 120) & (r - g > 50) & (r - b > 50)
    return white, dark, green, red


def find_bars(rgb, offset=(0, 0), skip_left=False, skip_right=False):  # Bars in an RGB array; offset is its top-left in screen coords.
    # skip_left/right: drop bars cut by that edge of the array, when it's a search window inside the frame (another mob's window has them whole)
    white, dark, green, red = colours(rgb)
    height, width = white.shape
    if height < bar_height + 2 or width < min_line + 1:
        return []
    lines = white[:-bar_height] & white[bar_height:]  # [y, x]: white in both the top line at y and the bottom line below it
    sums = np.concatenate((np.zeros((lines.shape[0], 1), np.int32), np.cumsum(lines, axis=1, dtype=np.int32)), axis=1)
    long_enough = np.zeros_like(lines)
    long_enough[:, :width - min_line + 1] = sums[:, min_line:] - sums[:, :width - min_line + 1] == min_line
    starts = long_enough & ~np.concatenate((np.zeros((lines.shape[0], 1), bool), lines[:, :-1]), axis=1)  # Left end of a long run
    bars = []
    for y, x in zip(*np.nonzero(starts)):
        if y < 1 or (skip_left and x == 0) or (skip_right and x + bar_width > width) or x + fill_start + 1 >= width:
            continue
        inside = slice(x + 2, x + min_line)  # Between the frame's edges, the rows next to both lines are black
        if dark[y + 1, inside].mean() < 0.7 or dark[y + bar_height - 1, inside].mean() < 0.7:
            continue
        row, first = y + fill_row, x + fill_start
        if not (green[row, first] or red[row, first]):  # The fill always starts at the left edge
            continue
        fill = green[row, first:first + fill_length]
        length = int(np.argmin(fill)) if not fill.all() else len(fill)
        end = first + length
        covered = end < min(width, first + fill_length) and not (red[row, end] or dark[row, end])  # Neither lost health nor empty bar
        bars.append(Bar(int(x + offset[0]), int(y + offset[1]), length / fill_length, bool(covered)))
    return bars


def read(frame, frame_rect, mobs):  # Sets .health on each mob Rect (screen coords): share left from its bar, or None without one
    for mob in mobs:
        mob.health = None
    if frame is None or frame_rect is None or not mobs:
        return
    bars = {}
    for mob in mobs:  # Only look where a bar could be, above each mob, with a margin so its own bar is never cut by the window's edge
        x1 = max(0, int(mob.center_x - max_offset - bar_width / 2 - frame_rect[0]) - 5)
        x2 = min(frame.width, int(mob.center_x + max_offset + bar_width / 2 - frame_rect[0]) + 6)
        y1 = max(0, int(mob.y1 - search_above - bar_height - 2 - frame_rect[1]))
        y2 = min(frame.height, int(mob.y1 + search_below + 2 - frame_rect[1]))
        if x2 - x1 < min_line or y2 - y1 < bar_height + 3:
            continue
        rgb = np.asarray(frame.crop((x1, y1, x2, y2)).convert("RGB"))
        for bar in find_bars(rgb, (x1 + frame_rect[0], y1 + frame_rect[1]), skip_left=x1 > 0, skip_right=x2 < frame.width):
            bars[(bar.x, bar.y)] = bar  # Windows of nearby mobs overlap: the same bar is found once
    assign(list(bars.values()), mobs)


def assign(bars, mobs):  # Gives each bar to the closest mob it can belong to, so two bunched-up mobs don't share one
    pairs = []
    for bar in bars:
        bottom = bar.y + bar_height
        for mob in mobs:
            dx = abs(bar.center_x - mob.center_x)
            if dx <= max_offset and mob.y1 - search_above <= bottom <= mob.y1 + search_below:
                pairs.append((dx + abs(bottom - (mob.y1 - 20)) / 4, id(bar), bar, mob))
    used_bars, used_mobs = set(), set()
    for _, _, bar, mob in sorted(pairs, key=lambda p: (p[0], p[1])):
        if id(bar) in used_bars or id(mob) in used_mobs:
            continue
        used_bars.add(id(bar))
        used_mobs.add(id(mob))
        mob.health = bar.health
