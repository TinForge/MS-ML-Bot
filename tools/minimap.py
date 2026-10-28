# Reads the minimap: where its map area is, the player's dot on it, other markers and which map this is

import hashlib
from dataclasses import dataclass, field

import cv2
import numpy as np
from PIL import Image

from tools import screen

title = cv2.cvtColor(np.asarray(Image.open("resources/minimap title.png").convert("RGB")), cv2.COLOR_RGB2GRAY)  # "MINI MAP" strip, same in every map
title_tolerance = 20  # Summed squared grey difference allowed per pixel when matching the title strip
player_sprite = np.asarray(Image.open("resources/minimap player.png"))  # Yellow dot in a dark ring; alpha marks the dot's own pixels
player_mask = cv2.merge([player_sprite[:, :, 3]] * 3)
player_sprite = np.ascontiguousarray(player_sprite[:, :, :3])
player_tolerance = 500  # Summed squared colour difference allowed; the dot is drawn identically everywhere
player_core = (255, 221, 68)  # The dot's centre colour
window_size = (460, 260)  # Largest minimap window expected, used to crop around its last position
search_margin = 20  # Pixels around the last title position searched first; the whole frame is searched if it moved

map_offset = (2, 67)  # Map area's top-left relative to the title strip's top-left
separator_offset = 66  # Row of the light line above the map area, relative to the title strip
name_area = (47, 24, 200, 52)  # Map name text relative to the title strip: x1, y1, x2, y2

# Marker colours (RGB ranges) and the size range of a marker's core, in pixels
MARKERS = {
    "other": ((200, 255), (0, 70), (0, 70)),  # Red: other players
    "npc": ((0, 120), (170, 255), (0, 120)),  # Green: NPCs
}
marker_area = (6, 80)


@dataclass
class Minimap:
    map_rect: tuple  # Map area in frame coords (x1, y1, x2, y2)
    player: tuple = None  # Player dot centre in map area coords (x, y), or None if not visible
    others: list = field(default_factory=list)  # Other players' dot centres
    npcs: list = field(default_factory=list)
    map_id: str = None  # Stable id of the map, from its name in the minimap header
    name: np.ndarray = None  # Map name pixels (bool array), for display
    area: np.ndarray = None  # Map area pixels (RGB), for stitching the scrolling minimap together
    markers: np.ndarray = None  # Bool mask over area of markers that move (players), left out when stitching
    position: tuple = None  # Player dot in map coords that don't change as the minimap scrolls; set by minimap_mosaic

    @property
    def size(self):
        return self.map_rect[2] - self.map_rect[0], self.map_rect[3] - self.map_rect[1]


def find_title(grey, near=None, full_search=True):  # Top-left of the title strip in the frame, or None
    h, w = title.shape
    if near is not None:  # The minimap rarely moves, so look where it was first
        x, y = near
        x1, y1 = max(0, x - search_margin), max(0, y - search_margin)
        loc = match_title(grey[y1:y + h + search_margin, x1:x + w + search_margin])
        if loc is not None:
            return loc[0] + x1, loc[1] + y1
    return match_title(grey) if full_search else None


def match_title(grey):
    if grey.shape[0] < title.shape[0] or grey.shape[1] < title.shape[1]:
        return None
    result = cv2.matchTemplate(grey, title, cv2.TM_SQDIFF)
    min_val, _, loc, _ = cv2.minMaxLoc(result)
    if min_val > title.size * title_tolerance:
        return None
    return loc


def find_map_rect(rgb, title_pos):  # Map area below the header, bounded by the window's light border lines
    tx, ty = title_pos
    left, top = tx + map_offset[0], ty + map_offset[1]
    separator = rgb[ty + separator_offset, tx:].min(axis=1) > 240  # Light line spanning the window's width
    run = np.flatnonzero(~separator)
    right = tx + (run[0] if len(run) else separator.size) - 3  # The line runs 3 px past the map area
    if right - left < 20:
        return None
    for y in range(top + 10, rgb.shape[0]):  # First fully light row is the line under the map area
        if rgb[y, left:right].min() > 235:
            return left, top, right, y
    return None


def find_player(area):  # Centre of the yellow dot, matched as a sprite since the map art can be yellow too
    h, w = player_sprite.shape[:2]
    core = cv2.inRange(area, player_core, player_core)  # Candidates first: the dot's centre colour, much cheaper than matching everywhere
    count, _, stats, centroids = cv2.connectedComponentsWithStats(core)
    for i in range(1, count):
        if not 8 <= stats[i, cv2.CC_STAT_AREA] <= 16:
            continue
        x, y = int(round(centroids[i][0] - (w - 1) / 2)), int(round(centroids[i][1] - (h - 1) / 2))
        window = area[max(0, y - 1):y + h + 1, max(0, x - 1):x + w + 1]  # 1 px slack around the expected spot
        if window.shape[0] < h or window.shape[1] < w:
            continue
        result = cv2.matchTemplate(np.ascontiguousarray(window), player_sprite, cv2.TM_SQDIFF, mask=player_mask)
        min_val, _, (mx, my), _ = cv2.minMaxLoc(result)
        if min_val <= player_tolerance:
            return max(0, x - 1) + mx + (w - 1) / 2, max(0, y - 1) + my + (h - 1) / 2
    return None


def find_markers(area, colour):  # Centres of marker-sized blobs of this colour
    (r1, r2), (g1, g2), (b1, b2) = colour
    mask = cv2.inRange(area, (r1, g1, b1), (r2, g2, b2))
    count, _, stats, centroids = cv2.connectedComponentsWithStats(mask)
    return [tuple(centroids[i]) for i in range(1, count) if marker_area[0] <= stats[i, cv2.CC_STAT_AREA] <= marker_area[1]]


def marker_mask(area, player):  # Pixels covered by moving markers, with a margin for their rings
    mask = cv2.inRange(area, *zip(*MARKERS["other"]))
    if player is not None:
        px, py = int(player[0]), int(player[1])
        cv2.rectangle(mask, (px - 4, py - 4), (px + 5, py + 5), 255, -1)
    return cv2.dilate(mask, np.ones((7, 7), np.uint8)) > 0


def read_name(rgb, title_pos, map_rect):  # Map name text pixels and an id made from them
    tx, ty = title_pos
    x1, y1, x2, y2 = name_area
    text = rgb[ty + y1:ty + y2, tx + x1:min(tx + x2, map_rect[2])].min(axis=2) > 220  # Near-white bold text on the blue header
    rows, cols = np.flatnonzero(text.any(axis=1)), np.flatnonzero(text.any(axis=0))
    if len(rows) == 0:
        return None, None
    text = text[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    return hashlib.sha1(np.packbits(text).tobytes() + bytes(text.shape)).hexdigest()[:12], text


def read(im, last_title=None):  # Minimap from a game area frame, and where its title was (for the next call); None if not shown
    rgb = screen.pixels(im)
    if last_title is not None:  # Usually still there: only look around it
        x, y = last_title
        ox, oy = max(0, x - search_margin), max(0, y - search_margin)
        region = rgb[oy:min(rgb.shape[0], y + window_size[1]), ox:min(rgb.shape[1], x + window_size[0])]
        result = read_region(region, (x - ox, y - oy), (ox, oy))
        if result[1] is not None:
            return result
    return read_region(rgb, None, (0, 0))


def read_region(rgb, near, offset):  # Like read, on part of the frame (an RGB array) starting at offset
    title_pos = find_title(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), near, full_search=near is None)  # A cropped region may not hold a window found elsewhere
    if title_pos is None:
        return None, None
    found = (title_pos[0] + offset[0], title_pos[1] + offset[1])
    map_rect = find_map_rect(rgb, title_pos)
    if map_rect is None:  # Minimised: only the title bar is showing
        return None, found
    x1, y1, x2, y2 = map_rect
    area = rgb[y1:y2, x1:x2]
    map_id, name = read_name(rgb, title_pos, map_rect)
    player = find_player(area)
    minimap = Minimap((x1 + offset[0], y1 + offset[1], x2 + offset[0], y2 + offset[1]), player,
                      find_markers(area, MARKERS["other"]), find_markers(area, MARKERS["npc"]), map_id, name,
                      area.copy(), marker_mask(area, player))
    return minimap, found
