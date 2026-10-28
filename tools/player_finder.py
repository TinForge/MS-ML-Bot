# Finds the player's character by matching their name from the status bar against nametags on screen

import cv2
import numpy as np
from data import config
from tools import screen, stat_reader

text_threshold = 200  # Name text is near white, both in the status bar and on nametags
name_area = (-140, 10, -12, 28)  # Where the name sits relative to the HP label: x1, y1, x2, y2
nametag_tolerance = config.nametag_tolerance  # Fraction of mismatched pixels allowed when matching a nametag
character_size = config.character_size  # Approximate sprite size, standing directly above the nametag
search_margin = config.search_margin  # Pixels around the last nametag searched first; the whole screen is searched if it's not there


def white_mask(rgb):
    return rgb.min(axis=2) > text_threshold


def read_name(im):  # Name pixels (bool array) from the status bar of a game area frame, or None
    rgb = screen.pixels(im)
    strip = rgb[max(0, rgb.shape[0] - stat_reader.search_height):]
    label = stat_reader.find_label(stat_reader.text_mask(strip), 'HP')
    if label is None:
        return None
    x, y = label
    x1, y1, x2, y2 = name_area
    area = white_mask(strip[max(0, y + y1):y + y2, max(0, x + x1):max(0, x + x2)])
    rows, cols = np.flatnonzero(area.any(axis=1)), np.flatnonzero(area.any(axis=0))
    if len(rows) == 0:
        return None
    return area[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


def match(scene, name):  # Top-left of the name in this RGB array, or None
    if scene.shape[0] < name.shape[0] or scene.shape[1] < name.shape[1]:
        return None
    scene = cv2.inRange(scene, (text_threshold + 1,) * 3, (255,) * 3) // 255  # Same as white_mask, but much faster on a whole frame
    result = cv2.matchTemplate(scene, name.astype(np.uint8), cv2.TM_SQDIFF)  # Counts mismatched pixels
    min_val, _, loc, _ = cv2.minMaxLoc(result)
    if min_val > name.size * nametag_tolerance:
        return None
    return loc


def find_nametag(im, name, near=None):  # Top-left of the player's nametag in image coords, or None
    if name is None:
        return None
    rgb = screen.pixels(im)
    height, width = rgb.shape[:2]
    bottom = height - stat_reader.search_height  # Leaves out the status bar, which shows the name too
    if near is not None:  # Characters move little between frames, so a small area around the last nametag usually has it
        x, y = near
        margin_x, margin_y = search_margin
        x1, y1 = max(0, x - margin_x), max(0, y - margin_y)
        x2, y2 = min(width, x + name.shape[1] + margin_x), min(bottom, y + name.shape[0] + margin_y)
        loc = match(rgb[y1:y2, x1:x2], name)
        if loc is not None:
            return loc[0] + x1, loc[1] + y1
    return match(rgb[:max(bottom, 0)], name)


def character_rect(nametag, name):  # Character rect (x1, y1, x2, y2), standing directly above the nametag
    x, y = nametag
    center_x = x + name.shape[1] / 2
    width, height = character_size
    return (center_x - width / 2, y - height - 2, center_x + width / 2, y - 2)
