# Records the platforms and ladders the player walks and climbs, in map coords saved per map

import bisect
import json
import os
from collections import deque

import cv2
import numpy as np

from tools import movement
from tools.camera import CameraTracker

folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")  # maps/<map id>/platforms.json

bin_size = 4  # Ground is recorded in columns this many pixels wide
merge_height = 6  # Ground points within this height in a column are the same platform
min_line_samples = 3  # Samples a platform line needs, so a stray reading never becomes a platform but one walk along it does
max_gap = 3  # Empty columns a platform line may jump over (unrecorded bits, not real gaps)
ladder_merge = 8  # Ladder points within this x distance are the same ladder
min_ladder_count = 5
calibration_samples = 40  # Samples needed, with enough minimap movement, before measuring the minimap's scale
calibration_spread = 12  # Minimap pixels the dot must have moved across before measuring the scale
anchor_samples = 8  # Recent samples used to tie camera coords to map coords
save_interval = 5.0


class Calibration:  # Relates camera coords (reset each session) to map coords: game pixels lined up with the minimap
    def __init__(self, scale=None):
        self.scale = scale  # Game pixels per minimap pixel, saved per map once measured
        self.samples = deque(maxlen=400)  # (camera x, camera y, minimap x, minimap y)
        self.offset = None  # camera coords - map coords

    @property
    def anchored(self):
        return self.offset is not None

    def reset(self):  # Camera coords jumped: tie them to the map again from new samples
        self.samples.clear()
        self.offset = None

    def add(self, position, minimap_position):
        self.samples.append((*position, *minimap_position))
        if self.scale is None:
            self.measure_scale()
        if self.scale is not None:
            self.anchor()

    def measure_scale(self):
        if len(self.samples) < calibration_samples:
            return
        s = np.array(self.samples)
        num = den = 0.0
        for axis in (0, 1):  # One scale for both axes, from whichever moved enough
            if np.ptp(s[:, axis + 2]) >= calibration_spread:
                w, m = s[:, axis] - s[:, axis].mean(), s[:, axis + 2] - s[:, axis + 2].mean()
                num, den = num + (w * m).sum(), den + (m * m).sum()
        if den > 0:
            self.scale = num / den

    def anchor(self):
        recent = np.array(list(self.samples)[-anchor_samples * 4:])
        if len(recent) < anchor_samples:
            self.offset = None
            return
        offsets = recent[:, :2] - self.scale * recent[:, 2:]
        offset = np.median(offsets, axis=0)
        if np.abs(offsets[-1] - offset).max() > 2 * self.scale:  # Latest sample disagrees: the camera coords jumped
            self.reset()
            return
        self.offset = tuple(offset)

    def to_map(self, position):
        return position[0] - self.offset[0], position[1] - self.offset[1]

    def to_camera(self, point):
        return point[0] + self.offset[0], point[1] + self.offset[1]


class PlatformMap:  # Ground and ladders recorded on one map
    def __init__(self):
        self.ground = {}  # Column index: [[height, times stood on], ...]
        self.ladders = []  # {"x", "top", "bottom", "count"}
        self.dirty = False

    def add_ground(self, x, y):
        column = self.ground.setdefault(int(x // bin_size), [])
        for cluster in column:
            if abs(cluster[0] - y) <= merge_height:
                cluster[0] += (y - cluster[0]) / (cluster[1] + 1)
                cluster[1] += 1
                break
        else:
            column.append([y, 1])
        self.dirty = True

    def add_ladder(self, x, y):
        for ladder in self.ladders:
            if abs(ladder["x"] - x) <= ladder_merge:
                ladder["x"] += (x - ladder["x"]) / (ladder["count"] + 1)
                ladder["top"], ladder["bottom"] = min(ladder["top"], y), max(ladder["bottom"], y)
                ladder["count"] += 1
                break
        else:
            self.ladders.append({"x": x, "top": y, "bottom": y, "count": 1})
        self.dirty = True

    def platforms(self):  # Confirmed ground as polylines [(x, y), ...], slopes included
        counts = {(b, c[0]): c[1] for b, column in self.ground.items() for c in column}
        columns = {b: sorted(c[0] for c in column) for b, column in self.ground.items()}
        points = sorted((b, y) for b, ys in columns.items() for y in ys)
        used = set()
        lines = []
        for start in points:
            if start in used:
                continue
            chain = [start]
            used.add(start)
            while True:
                b, y = chain[-1]
                nexts = []
                for nb in range(b + 1, b + max_gap + 2):  # Next few columns, only heights within reach of a walkable slope
                    ys, reach = columns.get(nb, ()), merge_height + movement.max_slope * bin_size * (nb - b)
                    i = bisect.bisect_left(ys, y - reach)
                    while i < len(ys) and ys[i] <= y + reach:
                        if (nb, ys[i]) not in used:
                            nexts.append((nb, ys[i]))
                        i += 1
                if not nexts:
                    break
                step = min(nexts, key=lambda p: (p[0] - b, abs(p[1] - y)))
                chain.append(step)
                used.add(step)
            if sum(counts[p] for p in chain) < min_line_samples:
                continue
            xy = np.array([((b + 0.5) * bin_size, y) for b, y in chain], dtype=np.float32)
            if len(xy) == 1:
                xy = np.array([[xy[0][0] - bin_size / 2, xy[0][1]], [xy[0][0] + bin_size / 2, xy[0][1]]], dtype=np.float32)
            lines.append([tuple(p) for p in cv2.approxPolyDP(xy.reshape(-1, 1, 2), 1.5, False).reshape(-1, 2)])
        return lines

    def confirmed_ladders(self):
        return [ladder for ladder in self.ladders if ladder["count"] >= min_ladder_count and ladder["bottom"] - ladder["top"] >= 10]

    def to_json(self):
        return {"ground": {str(b): column for b, column in self.ground.items()}, "ladders": self.ladders}

    @classmethod
    def from_json(cls, data):
        m = cls()
        m.ground = {int(b): [list(c) for c in column] for b, column in data.get("ground", {}).items()}
        m.ladders = [dict(ladder) for ladder in data.get("ladders", [])]
        return m


class Mapper:  # Follows the player through the camera and minimap, and records platforms while asked to
    def __init__(self):
        self.camera = CameraTracker()
        self.movement = movement.MovementState()
        self.map_id = None
        self.calibration = None
        self.platforms = None
        self.feet = None  # Player's feet in map coords, or None until anchored
        self.last_save = 0
        self.lines = []  # Finished copies of the recorded platforms and ladders, safe to draw from another thread
        self.ladders = []
        self.last_lines = 0

    def path(self, map_id=None):
        return os.path.join(folder, map_id or self.map_id, "platforms.json")

    def switch(self, map_id):  # Saves what was recorded on the old map and loads the new one's
        self.save()
        self.map_id = map_id
        self.camera.reset()
        self.movement.reset()
        try:
            with open(self.path()) as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = {}
        self.calibration = Calibration(data.get("scale"))
        self.platforms = PlatformMap.from_json(data)
        self.publish()

    def save(self):
        if self.map_id is None or self.platforms is None or not (self.platforms.dirty or self.calibration.scale is not None):
            return
        os.makedirs(os.path.dirname(self.path()), exist_ok=True)
        with open(self.path(), "w") as f:
            json.dump({"scale": self.calibration.scale, **self.platforms.to_json()}, f)
        self.platforms.dirty = False

    def update(self, frame, frame_rect, player_rect, minimap, now, record):  # frame: PIL game area; rects in screen coords
        if minimap is not None and minimap.map_id is not None and minimap.map_id != self.map_id:
            self.switch(minimap.map_id)
        self.camera.update(frame)
        self.feet = None
        if self.calibration is None:
            return
        if self.camera.lost:  # Camera coords jumped: start following again
            self.movement.reset()
            self.calibration.reset()
        if player_rect is None:
            return
        cx, cy = self.camera.position
        position = (cx + (player_rect[0] + player_rect[2]) / 2 - frame_rect[0], cy + player_rect[3] - frame_rect[1])
        state = self.movement.update(now, *position)
        if minimap is not None and minimap.position is not None:
            self.calibration.add(position, minimap.position)
        if not self.calibration.anchored:
            return
        self.feet = self.calibration.to_map(position)
        if record and state == movement.GROUND and self.movement.steady >= 3:
            self.platforms.add_ground(*self.feet)
        elif record and state == movement.LADDER and self.movement.steady >= 2:
            self.platforms.add_ladder(*self.feet)
        if self.platforms.dirty and now - self.last_lines >= 0.5:
            self.publish()
            self.last_lines = now
        if self.platforms.dirty and now - self.last_save >= save_interval:
            self.save()
            self.last_save = now

    def publish(self):
        self.lines = self.platforms.platforms()
        self.ladders = [dict(ladder) for ladder in self.platforms.confirmed_ladders()]

    def to_screen(self, point, frame_rect):  # Map coords to screen coords, for drawing; None until anchored
        calibration = self.calibration
        offset = calibration.offset if calibration is not None else None  # Read once: the detection thread may reset it meanwhile
        if offset is None:
            return None
        camera_x, camera_y = self.camera.position
        return point[0] + offset[0] - camera_x + frame_rect[0], point[1] + offset[1] - camera_y + frame_rect[1]

    @property
    def state(self):
        return self.movement.state
