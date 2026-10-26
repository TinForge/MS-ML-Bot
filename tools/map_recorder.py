# Records the platforms and ladders the player walks and climbs, in map coords saved per map. While detection runs it also
# learns where mobs go on that recorded ground (never adding ground of its own), so safe stretches can be told from spawn areas

import bisect
import json
import os
from collections import deque

import cv2
import numpy as np

from data import rects
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
ladder_width = 16  # Width of the box navigation gets for a recorded ladder (feet positions are a single line)
mob_ground_margin = 15  # How far a mob's feet may be from recorded ground and still count as standing on it
max_learn_step = 0.5  # Longest gap between frames counted as watching, so a pause isn't taken for a long look
learn_time = 30.0  # Seconds a stretch of ground must have been on screen before it's judged
safe_share = 0.01  # Share of the watched time with mobs on it below which ground is safe
busy_share = 0.1  # ... and above which it's busy (a spawn area); occasional in between
safety_interval = 2.0  # Seconds between working out the safety of each stretch again
SAFE, OCCASIONAL, BUSY, UNKNOWN = "safe", "occasional", "busy", "unknown"


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
        self.ground = {}  # Column index: [[height, times stood on, seconds with mobs on it, seconds on screen], ...]
        self.ladders = []  # {"x", "top", "bottom", "count"}
        self.dirty = False  # Ground or ladders changed: lines need working out again
        self.learned = False  # Mob statistics changed: safety needs working out again

    def add_ground(self, x, y):
        column = self.ground.setdefault(int(x // bin_size), [])
        for cluster in column:
            if abs(cluster[0] - y) <= merge_height:
                cluster[0] += (y - cluster[0]) / (cluster[1] + 1)
                cluster[1] += 1
                break
        else:
            column.append([y, 1, 0.0, 0.0])
        self.dirty = True

    def see(self, view, mobs, seconds):  # A frame's worth of watching: view (x1, y1, x2, y2) of the map on screen, mobs (x1, x2, feet y)
        # in map coords. Only ground already recorded learns anything; mobs never add ground
        x1, y1, x2, y2 = view
        for b in range(int(x1 // bin_size), int(x2 // bin_size) + 1):
            for cluster in self.ground.get(b, ()):
                if y1 <= cluster[0] <= y2:
                    cluster[3] += seconds
        for mx1, mx2, feet in mobs:
            for b in range(int(mx1 // bin_size), int(mx2 // bin_size) + 1):  # The ground under its whole box
                cluster = min(self.ground.get(b, ()), key=lambda c: abs(c[0] - feet), default=None)
                if cluster is not None and abs(cluster[0] - feet) <= mob_ground_margin:
                    cluster[2] += seconds
        self.learned = True

    def safety_at(self, x, y):  # SAFE, OCCASIONAL, BUSY or UNKNOWN for the recorded ground at map (x, y)
        cluster = min(self.ground.get(int(x // bin_size), ()), key=lambda c: abs(c[0] - y), default=None)
        if cluster is None or abs(cluster[0] - y) > merge_height or cluster[3] < learn_time:
            return UNKNOWN
        share = cluster[2] / cluster[3]
        return SAFE if share < safe_share else OCCASIONAL if share < busy_share else BUSY

    def safety_runs(self, lines):  # Each platform line split into runs of the same safety: [(safety, [(x, y), ...]), ...]
        runs = []
        for line in lines:
            xs = np.arange(line[0][0], line[-1][0] + bin_size, bin_size)
            ys = np.interp(xs, [p[0] for p in line], [p[1] for p in line])
            current, points = None, []
            for x, y in zip(xs.tolist(), ys.tolist()):
                safety = self.safety_at(x, y)
                if safety != current and points:
                    runs.append((current, points + [(x, y)]))  # Joined to the next run's start, so the line has no gaps
                    points = []
                current = safety
                points.append((x, y))
            if len(points) >= 2:
                runs.append((current, points))
        return runs

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
        m.ground = {int(b): [list(c) + [0.0] * (4 - len(c)) for c in column] for b, column in data.get("ground", {}).items()}  # Older files: no mob statistics
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
        self.safety = []  # Finished copy of PlatformMap.safety_runs, for drawing
        self.last_safety = 0
        self.last_learn = None  # When mobs were last learned from, for how long the ground has been watched
        self.last_lines = 0
        self.frame_rect = None  # Screen rect of the last game area followed, for turning map coords into screen coords

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
        if self.map_id is None or self.platforms is None or not (self.platforms.dirty or self.platforms.learned or self.calibration.scale is not None):
            return
        os.makedirs(os.path.dirname(self.path()), exist_ok=True)
        with open(self.path(), "w") as f:
            json.dump({"scale": self.calibration.scale, **self.platforms.to_json()}, f)
        self.platforms.dirty = self.platforms.learned = False

    def update(self, frame, frame_rect, player_rect, minimap, now, record, mobs=None):  # frame: PIL game area; rects in screen coords;
        # mobs: this frame's detected Mob rects, None when detection isn't running (nothing to learn from)
        if minimap is not None and minimap.map_id is not None and minimap.map_id != self.map_id:
            self.switch(minimap.map_id)
        self.camera.update(frame)
        self.frame_rect = frame_rect
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
        self.learn(mobs, frame_rect, now)
        if self.platforms.dirty and now - self.last_lines >= 0.5:
            self.publish()
            self.last_lines = now
        if self.platforms.learned and now - self.last_safety >= safety_interval:
            self.safety = self.platforms.safety_runs(self.lines)
            self.last_safety = now
        if (self.platforms.dirty or self.platforms.learned) and now - self.last_save >= save_interval:
            self.save()
            self.last_save = now

    def learn(self, mobs, frame_rect, now):  # Counts how long the ground on screen was watched, and where mobs stood on it
        last, self.last_learn = self.last_learn, (now if mobs is not None else None)
        shift = self.screen_shift(frame_rect)
        if mobs is None or last is None or shift is None:
            return
        dx, dy = shift
        view = (frame_rect[0] - dx, frame_rect[1] - dy, frame_rect[2] - dx, frame_rect[3] - dy)
        self.platforms.see(view, [(m.x1 - dx, m.x2 - dx, m.y2 - dy) for m in mobs], min(now - last, max_learn_step))

    def publish(self):
        self.lines = self.platforms.platforms()
        self.ladders = [dict(ladder) for ladder in self.platforms.confirmed_ladders()]
        self.safety = self.platforms.safety_runs(self.lines)

    def to_screen(self, point, frame_rect):  # Map coords to screen coords, for drawing; None until anchored
        shift = self.screen_shift(frame_rect)
        return (point[0] + shift[0], point[1] + shift[1]) if shift is not None else None

    def screen_shift(self, frame_rect):  # What to add to map coords to get screen coords, or None until anchored
        calibration = self.calibration
        offset = calibration.offset if calibration is not None else None  # Read once: the detection thread may reset it meanwhile
        if offset is None or frame_rect is None:
            return None
        camera_x, camera_y = self.camera.position
        return offset[0] - camera_x + frame_rect[0], offset[1] - camera_y + frame_rect[1]

    def screen_rects(self):  # Recorded platforms and ladders on screen, as Rects for navigation; [] until anchored
        frame_rect = self.frame_rect
        shift = self.screen_shift(frame_rect)
        if shift is None:
            return []
        dx, dy = shift
        on_screen = lambda x1, y1, x2, y2: x2 >= frame_rect[0] and x1 <= frame_rect[2] and y2 >= frame_rect[1] and y1 <= frame_rect[3]
        found = []
        for line in self.lines:
            platform = rects.PlatformLine([(x + dx, y + dy) for x, y in line])
            if on_screen(platform.x1, platform.y1, platform.x2, platform.y2):
                found.append(platform)
        for ladder in self.ladders:
            x, top, bottom = ladder["x"] + dx, ladder["top"] + dy, ladder["bottom"] + dy
            if on_screen(x, top, x, bottom):
                found.append(rects.Rect("Ladder", "yellow", x - ladder_width / 2, top, x + ladder_width / 2, bottom, 1))
        return found

    @property
    def state(self):
        return self.movement.state
