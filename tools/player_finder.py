# Finds the player's character by matching their name from the status bar against nametags on screen

import cv2
import numpy as np
from tools import stat_reader

text_threshold = 200  # Name text is near white, both in the status bar and on nametags
name_area = (-140, 10, -12, 28)  # Where the name sits relative to the HP label: x1, y1, x2, y2
nametag_tolerance = 0.05  # Fraction of mismatched pixels allowed when matching a nametag
character_size = (50, 66)  # Approximate sprite size, standing directly above the nametag


def white_mask(rgb):
    return rgb.min(axis=2) > text_threshold


def read_name(im):  # Name pixels (bool array) from the status bar of a game area image, or None
    strip = np.asarray(im.crop((0, max(0, im.height - stat_reader.search_height), im.width, im.height)))
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


def find_player(im, name):  # Character rect (x1, y1, x2, y2) in image coords, or None
    if name is None:
        return None
    scene = np.asarray(im)[:im.height - stat_reader.search_height]  # Leaves out the status bar, which shows the name too
    if scene.shape[0] < name.shape[0] or scene.shape[1] < name.shape[1]:
        return None
    scene = cv2.inRange(scene, (text_threshold + 1,) * 3, (255,) * 3) // 255  # Same as white_mask, but much faster on a whole frame
    result = cv2.matchTemplate(scene, name.astype(np.uint8), cv2.TM_SQDIFF)  # Counts mismatched pixels
    min_val, _, (x, y), _ = cv2.minMaxLoc(result)
    if min_val > name.size * nametag_tolerance:
        return None
    center_x = x + name.shape[1] / 2
    width, height = character_size
    return (center_x - width / 2, y - height - 2, center_x + width / 2, y - 2)
