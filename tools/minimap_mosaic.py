# Stitches the scrolling minimap into one picture per map, so the player's dot gets coordinates that stay put while it scrolls

import json
import os
import time

import cv2
import numpy as np
from PIL import Image

folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")  # maps/<map id>/minimap.png + .json

patch_margin = 0.25  # Each view is located by its central part (minus this fraction per side), which is the most likely to be known already
close_level = 8  # Grey levels within which a pixel counts as matching
step_match = 0.6  # Fraction of pixels that must match the previous view; the minimap is see-through, so the game behind it changes some
picture_match = 0.4  # Same, against the saved picture (used after a jump or when a session starts), which holds an older background
picture_lead = 0.15  # ... and the best position must match that much better than any other, so a lookalike isn't taken
save_interval = 5.0  # Seconds between saves while the picture keeps growing
restart_after = 5.0  # Seconds the view can't be found in the saved picture before a map with nothing recorded on it starts a new one: on
# maps of repeating platforms seen through a see-through minimap, the saved picture can match several places equally


class Mosaic:  # The stitched minimap of one map
    def __init__(self, map_id, load=True):
        self.map_id = map_id
        self.image = None  # RGB picture of everything seen so far
        self.known = None  # Bool mask of pixels seen so far
        self.origin = (0, 0)  # Where map coords (0, 0) are in the picture; the first view's top-left
        self.last = None  # Last view position in picture coords
        self.previous = None  # Last view (grey) and its moving-marker mask
        self.dirty = False
        self.last_save = 0
        self.unplaced_since = None  # When the views started failing to be placed in the saved picture, this session
        if load:
            self.load()

    def path(self, name):
        return os.path.join(folder, self.map_id, name)

    def load(self):
        try:
            rgba = np.asarray(Image.open(self.path("minimap.png")).convert("RGBA"))
            with open(self.path("minimap.json")) as f:
                self.origin = tuple(json.load(f)["origin"])
        except (OSError, ValueError, KeyError):
            return
        self.image, self.known = np.ascontiguousarray(rgba[:, :, :3]), rgba[:, :, 3] > 0

    def save(self):
        os.makedirs(self.path(""), exist_ok=True)
        Image.fromarray(np.dstack([self.image, self.known.astype(np.uint8) * 255])).save(self.path("minimap.png"))
        with open(self.path("minimap.json"), "w") as f:
            json.dump({"origin": list(self.origin)}, f)
        self.dirty = False
        self.last_save = time.time()

    def update(self, view, moving):  # Adds a view; returns its top-left in map coords, or None if it can't be placed yet
        if self.image is None:
            self.image, self.known = np.zeros_like(view), np.zeros(view.shape[:2], bool)
            pos = (0, 0)
        else:
            pos = self.locate(view, moving)
            if pos is None:
                if self.unplaced_since is None:
                    self.unplaced_since = time.time()
                return None
        self.unplaced_since = None
        pos = self.grow(pos, view.shape[:2])
        self.last = pos
        self.previous = (cv2.cvtColor(np.ascontiguousarray(view), cv2.COLOR_RGB2GRAY), moving)
        new = ~moving & ~self.known[pos[1]:pos[1] + view.shape[0], pos[0]:pos[0] + view.shape[1]]
        if new.any():  # Only fill in what hasn't been seen; the platforms never change
            region = self.image[pos[1]:pos[1] + view.shape[0], pos[0]:pos[0] + view.shape[1]]
            region[new] = view[new]
            self.known[pos[1]:pos[1] + view.shape[0], pos[0]:pos[0] + view.shape[1]] |= new
            self.dirty = True
        if self.dirty and time.time() - self.last_save >= save_interval:
            self.save()
        return pos[0] - self.origin[0], pos[1] - self.origin[1]

    def locate(self, view, moving):  # View's top-left in picture coords
        h, w = view.shape[:2]
        mx, my = int(w * patch_margin), int(h * patch_margin)
        patch = cv2.cvtColor(np.ascontiguousarray(view[my:h - my, mx:w - mx]), cv2.COLOR_RGB2GRAY)
        mask = (~moving[my:h - my, mx:w - mx]).astype(np.uint8) * 255
        if mask.sum() == 0:
            return None
        if self.last is not None and self.previous is not None and self.previous[0].shape == view.shape[:2]:
            # Compare with the previous view: the game showing through the minimap barely changes between two reads,
            # and scroll steps are whole pixels, so adding them up doesn't drift
            loc = self.match(self.previous[0], patch, mask, step_match)
            if loc is not None:
                return self.last[0] + loc[0] - mx, self.last[1] + loc[1] - my
        grey = cv2.cvtColor(self.image, cv2.COLOR_RGB2GRAY)  # After a jump or at the start: find the view in the saved picture
        grey[~self.known] = 0
        loc = self.match(grey, patch, mask, picture_match, picture_lead)
        return None if loc is None else (loc[0] - mx, loc[1] - my)


    @staticmethod
    def match(grey, patch, mask, min_match, lead=None):  # Best position of patch in grey, if enough of its pixels match there
        if grey.shape[0] < patch.shape[0] or grey.shape[1] < patch.shape[1]:
            return None
        result = cv2.matchTemplate(grey, patch, cv2.TM_SQDIFF, mask=mask)
        _, _, loc, _ = cv2.minMaxLoc(result)
        matched = Mosaic.matching(grey, patch, mask, loc)
        if matched < min_match:  # Not this view: e.g. scrolled somewhere not seen yet
            return None
        if lead is not None:  # Compare with the best position at least 3 px away
            x, y = loc
            result[max(0, y - 2):y + 3, max(0, x - 2):x + 3] = np.inf
            _, _, other, _ = cv2.minMaxLoc(result)
            if other != loc and matched - Mosaic.matching(grey, patch, mask, other) < lead:
                return None
        return loc

    @staticmethod
    def matching(grey, patch, mask, loc):  # Fraction of the patch's pixels that match grey at loc
        region = grey[loc[1]:loc[1] + patch.shape[0], loc[0]:loc[0] + patch.shape[1]]
        return np.count_nonzero((cv2.absdiff(region, patch) <= close_level) & (mask > 0)) / np.count_nonzero(mask)

    def grow(self, pos, size):  # Enlarges the picture so a view at pos fits; returns pos adjusted for any growth up or left
        x, y = pos
        h, w = size
        left, top = max(0, -x), max(0, -y)
        right, bottom = max(0, x + w - self.image.shape[1]), max(0, y + h - self.image.shape[0])
        if left or top or right or bottom:
            self.image = np.pad(self.image, ((top, bottom), (left, right), (0, 0)))
            self.known = np.pad(self.known, ((top, bottom), (left, right)))
            self.origin = (self.origin[0] + left, self.origin[1] + top)
            if self.last is not None:
                self.last = (self.last[0] + left, self.last[1] + top)
        return x + left, y + top


class Tracker:  # Keeps one mosaic per map and fills in each minimap reading's position
    def __init__(self):
        self.mosaic = None

    def update(self, minimap, restart_ok=False):  # restart_ok: nothing is recorded in this map's coords, so its saved picture can be
        # replaced when it can't be matched (see restart_after)
        if minimap is None or minimap.map_id is None:
            return
        if self.mosaic is None or self.mosaic.map_id != minimap.map_id:  # Changed map: keep what was seen of the old one
            if self.mosaic is not None and self.mosaic.dirty:
                self.mosaic.save()
            self.mosaic = Mosaic(minimap.map_id)
        view_pos = self.mosaic.update(minimap.area, minimap.markers)
        stuck = self.mosaic.unplaced_since
        if view_pos is None and restart_ok and self.mosaic.last is None and stuck is not None and time.time() - stuck >= restart_after:
            print("Minimap: this view isn't in the saved picture of the map, starting it again")
            self.mosaic = Mosaic(minimap.map_id, load=False)
            view_pos = self.mosaic.update(minimap.area, minimap.markers)
        if view_pos is not None and minimap.player is not None:
            minimap.position = (view_pos[0] + minimap.player[0], view_pos[1] + minimap.player[1])

    def save(self):
        if self.mosaic is not None and self.mosaic.dirty:
            self.mosaic.save()
