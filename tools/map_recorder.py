# Records the platforms and ladders the player walks and climbs, in map coords saved per map. While detection runs it also
# learns where mobs go on that recorded ground (never adding ground of its own), so safe stretches can be told from spawn areas

import bisect
import json
import os
import warnings
from collections import deque

import cv2
import numpy as np

from data import rects
from tools import movement
from tools.camera import CameraTracker

folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "maps")  # maps/<map id>/platforms.json

bin_size = 4  # Ground is recorded in columns this many pixels wide
erase_width = 24  # Erasing removes recorded ground this far either side of the feet (about the character's width in all)
erase_height = 20  # ... and this far above or below them: falling, the feet move ~22 px a frame, so a thin band would be skipped
merge_height = 10  # A new ground reading within this height of one already in its column is the same ground
duplicate_height = 30  # A piece lying this close along a longer platform is the same ground recorded twice (see without_duplicates):
# real platforms that overlap are at least a character's height apart (~60 px), or nothing could stand on the lower one
duplicate_share = 0.5  # ... over at least this share of its width
consolidate_height = 12  # Ground heights in a column this close are merged: they drift together as readings average out (the ones
# seen were 6-11 px apart). Kept small: where a stair step ends, one column can hold both steps' heights ~20 px apart
min_line_samples = 3  # Samples a platform line needs, so a stray reading never becomes a platform but one walk along it does
min_line_width = 24  # Narrowest platform kept: real ones are far wider, slivers this thin were recorded while hanging on a rope
max_gap = 3  # Empty columns a platform line may jump over (unrecorded bits, not real gaps)
ladder_merge = 40  # Rope readings this close sideways continue a rope (ropes are rarely anywhere near each other; climbing readings
# wander more than a few pixels, and at 8 px one rope was recorded as two side by side)...
ladder_gap = 30  # ... if they're also within this of its height range: ropes at the same x on different floors stay apart
on_rope_x = 8  # How close to a recorded rope's x the feet are on it: narrow, so ground beside a rope through a platform still records
min_ladder_count = 5
calibration_samples = 40  # Samples needed, with enough minimap movement, before measuring the minimap's scale
calibration_spread = 12  # Minimap pixels the dot must have moved across before measuring the scale
anchor_samples = 8  # Recent samples used to tie camera coords to map coords
jump_samples = 30  # Samples in a row (about a second) disagreeing with the anchor before the camera coords count as having jumped:
# the minimap dot trails the player, by a couple of minimap pixels in a fast drop, and one such sample used to start the anchoring
# over (the camera tracker catches real jumps itself)
save_interval = 5.0
ground_delay = 0.15  # Seconds a ground reading is held before it's recorded, dropped if the player leaves the ground meanwhile: the
# movement tracker takes 2-3 frames to see gravity, so walking off a ledge recorded a few pixels of platform past it, sagging
ladder_width = 16  # Width of the box navigation gets for a recorded ladder (feet positions are a single line)
mob_ground_margin = 15  # How far a mob's feet may be from recorded ground and still count as standing on it
max_learn_step = 0.5  # Longest gap between frames counted as watching, so a pause isn't taken for a long look
learn_time = 30.0  # Seconds a stretch of ground must have been on screen before it's judged
safe_share = 0.02  # Share of the watched time with a mob on or near it below which ground is safe
busy_share = 0.06  # ... and from which it's busy (a spawn area); occasional in between. Mobs wander and get killed, so even in a spawn
# area one spot has a mob on it only ~5-10% of the time: at 10% nothing was ever busy
danger_reach = 60  # Ground counts as being as busy as the busiest ground this close either side (about a mob's reach): what makes a
# spot unsafe is a mob near it, not only one standing right on it
safety_interval = 2.0  # Seconds between working out the safety of each stretch again
scroll_smoothing = 0.5  # Weight of each frame's camera speed in the running one used for drawing ahead (see draw_shift)
max_predict = 0.15  # Longest a drawing is moved on for: past that the frames have stopped coming, and guessing on would wander
SAFE, OCCASIONAL, BUSY, UNKNOWN = "safe", "occasional", "busy", "unknown"


def without_duplicates(lines):  # Drops pieces that lie along a longer platform, within duplicate_height of it, over at least
    # duplicate_share of their width: the same ground recorded twice. Stair steps only touch at an end, so they stay
    by_width = sorted(lines, key=lambda l: l[-1][0] - l[0][0], reverse=True)
    kept = []
    for line in by_width:
        xs, ys = [p[0] for p in line], [p[1] for p in line]
        width = max(xs[-1] - xs[0], bin_size)
        duplicate = False
        for other in kept:
            ox, oy = [p[0] for p in other], [p[1] for p in other]
            x1, x2 = max(xs[0], ox[0]), min(xs[-1], ox[-1])
            if x2 - x1 < duplicate_share * width:
                continue
            sample = np.linspace(x1, x2, 8)
            if np.abs(np.interp(sample, xs, ys) - np.interp(sample, ox, oy)).max() <= duplicate_height:
                duplicate = True
                break
        if not duplicate:
            kept.append(line)
    return [line for line in lines if any(line is k for k in kept)]  # In the order they were found


def consolidate(column):  # Merges ground heights in a column that are within consolidate_height: one ground recorded twice.
    # Heights are averaged by how often each was stood on, mob time added up, watched time kept (both were on screen together).
    # Returns whether anything merged
    merged = False
    column.sort(key=lambda c: c[0])
    i = 0
    while i < len(column) - 1:
        a, b = column[i], column[i + 1]
        if b[0] - a[0] <= consolidate_height:
            stood = a[1] + b[1]
            column[i] = [(a[0] * a[1] + b[0] * b[1]) / stood, stood, a[2] + b[2], max(a[3], b[3])]
            del column[i + 1]
            merged = True
        else:
            i += 1
    return merged


class Calibration:  # Relates camera coords (reset each session) to map coords: game pixels lined up with the minimap
    def __init__(self, scale=None):
        self.scale = scale  # Game pixels per minimap pixel, saved per map once measured
        self.samples = deque(maxlen=400)  # (camera x, camera y, minimap x, minimap y)
        self.offset = None  # camera coords - map coords
        self.disagreeing = 0  # Samples in a row far from the anchor

    @property
    def anchored(self):
        return self.offset is not None

    def reset(self):  # Camera coords jumped: tie them to the map again from new samples
        self.samples.clear()
        self.offset = None
        self.disagreeing = 0

    def add(self, position, minimap_position):
        self.samples.append((*position, *minimap_position))
        if self.scale is None:
            self.measure_scale()
        if self.scale is not None:
            self.anchor()

    def spread(self):  # Minimap pixels the dot has moved across (the more of the two directions) in the samples kept
        if len(self.samples) < 2:
            return 0.0
        s = np.array(self.samples)
        return float(max(np.ptp(s[:, 2]), np.ptp(s[:, 3])))

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
        if np.abs(offsets[-1] - offset).max() > 2 * self.scale:  # Latest sample disagrees: the dot trailing, or the camera coords jumped
            self.disagreeing += 1
            if self.disagreeing >= jump_samples:
                self.reset()
            return
        self.disagreeing = 0
        self.offset = tuple(offset)

    def to_map(self, position):
        return position[0] - self.offset[0], position[1] - self.offset[1]

    def to_camera(self, point):
        return point[0] + self.offset[0], point[1] + self.offset[1]


def continues(ladder, x, top, bottom):  # Whether rope readings at x from top to bottom are part of the recorded rope
    return abs(ladder["x"] - x) <= ladder_merge and top <= ladder["bottom"] + ladder_gap and bottom >= ladder["top"] - ladder_gap


def judge(share):  # SAFE, OCCASIONAL or BUSY for a share of the watched time with a mob on or near the ground
    return SAFE if share < safe_share else OCCASIONAL if share < busy_share else BUSY


class PlatformMap:  # Ground and ladders recorded on one map
    def __init__(self):
        self.ground = {}  # Column index: [[height, times stood on, seconds with mobs on it, seconds on screen], ...]
        self.ladders = []  # {"x", "top", "bottom", "count"}
        self.dirty = False  # Ground or ladders changed: lines need working out again
        self.learned = False  # Mob statistics changed: safety needs working out again

    def add_ground(self, x, y):
        column = self.ground.setdefault(int(x // bin_size), [])
        cluster = min(column, key=lambda c: abs(c[0] - y), default=None)
        if cluster is not None and abs(cluster[0] - y) <= merge_height:  # The nearest, not just the first close enough
            cluster[0] += (y - cluster[0]) / (cluster[1] + 1)
            cluster[1] += 1
            consolidate(column)
        else:
            column.append([y, 1, 0.0, 0.0])
        self.dirty = True

    def erase(self, x, y):  # Removes the ground around map (x, y), and any rope it's part-way up (at a rope's foot or top it's
        # standing on the ground there, which mustn't take the rope with it)
        removed = False
        for b in range(int((x - erase_width) // bin_size), int((x + erase_width) // bin_size) + 1):
            column = self.ground.get(b)
            if column:
                kept = [c for c in column if abs(c[0] - y) > erase_height]
                if len(kept) < len(column):
                    removed = True
                    if kept:
                        self.ground[b] = kept
                    else:
                        del self.ground[b]
        kept = [ladder for ladder in self.ladders if not (abs(ladder["x"] - x) <= on_rope_x and ladder["top"] + merge_height < y < ladder["bottom"] - merge_height)]
        if removed or len(kept) < len(self.ladders):
            self.ladders = kept
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
        b, reach = int(x // bin_size), int(danger_reach // bin_size)
        if np.isnan(self.share_at(b, y, merge_height)):
            return UNKNOWN
        return judge(np.nanmax([self.share_at(column, y) for column in range(b - reach, b + reach + 1)]))

    def share_at(self, b, y, within=2 * merge_height):  # Share of the watched time with a mob on the ground in column b at height y (its
        # own level, not ground above or below), NaN if there's none there watched for learn_time
        cluster = min(self.ground.get(b, ()), key=lambda c: abs(c[0] - y), default=None)
        if cluster is None or abs(cluster[0] - y) > within or cluster[3] < learn_time:
            return np.nan
        return cluster[2] / cluster[3]

    def activity(self, line):  # (seconds with mobs on it, seconds watched) per column, on average along a platform line, for where to
        # go looking (the same per-column measure as safety_at)
        mobs = watched = 0.0
        columns = 0
        xs, ys = [p[0] for p in line], [p[1] for p in line]
        for b in range(int(xs[0] // bin_size), int(xs[-1] // bin_size) + 1):  # Every column along it (the line keeps only its corners)
            y = float(np.interp((b + 0.5) * bin_size, xs, ys))
            cluster = min(self.ground.get(b, ()), key=lambda c: abs(c[0] - y), default=None)
            columns += 1
            if cluster is not None and abs(cluster[0] - y) <= merge_height:
                mobs, watched = mobs + cluster[2], watched + cluster[3]
        return (mobs / columns, watched / columns) if columns else (0.0, 0.0)

    def safety_runs(self, lines):  # Each platform line split into runs of the same safety: [(safety, [(x, y), ...]), ...]
        runs = []
        reach = int(danger_reach // bin_size)
        for line in lines:
            xs = np.arange(line[0][0], line[-1][0] + bin_size, bin_size)
            ys = np.interp(xs, [p[0] for p in line], [p[1] for p in line])
            bins = (xs // bin_size).astype(int)
            around = np.arange(bins[0] - reach, bins[-1] + reach + 1)  # Columns along it and within reach of its ends, at its height
            heights = np.interp(around * bin_size + bin_size / 2, [p[0] for p in line], [p[1] for p in line])
            shares = np.array([self.share_at(b, y) for b, y in zip(around.tolist(), heights.tolist())])
            windows = np.lib.stride_tricks.sliding_window_view(shares, 2 * reach + 1)[bins - bins[0]]  # Each column and its reach either side
            with np.errstate(all="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)  # All-NaN windows: unknown anyway
                nearby = np.nanmax(windows, axis=1)
            own = np.array([self.share_at(b, y, merge_height) for b, y in zip(bins.tolist(), ys.tolist())])
            current, points = None, []
            for x, y, mine, near in zip(xs.tolist(), ys.tolist(), own.tolist(), nearby.tolist()):
                safety = UNKNOWN if np.isnan(mine) else judge(near)
                if safety != current and points:
                    runs.append((current, points + [(x, y)]))  # Joined to the next run's start, so the line has no gaps
                    points = []
                current = safety
                points.append((x, y))
            if len(points) >= 2:
                runs.append((current, points))
        return runs

    def stretches(self, line, safety, min_width=0):  # (x1, x2) of each stretch of a platform line with that safety, at least min_width
        return [(points[0][0], points[-1][0]) for s, points in self.safety_runs([line]) if s == safety and points[-1][0] - points[0][0] >= min_width]

    def add_ladder(self, x, y):  # A reading on a rope: continues the nearest rope it's in line with, or starts a new one
        near = [ladder for ladder in self.ladders if continues(ladder, x, y, y)]
        if near:
            ladder = min(near, key=lambda r: abs(r["x"] - x))
            ladder["x"] += (x - ladder["x"]) / (ladder["count"] + 1)
            ladder["top"], ladder["bottom"] = min(ladder["top"], y), max(ladder["bottom"], y)
            ladder["count"] += 1
        else:
            self.ladders.append({"x": x, "top": y, "bottom": y, "count": 1})
        self.dirty = True

    def merge_ladders(self):  # Joins ropes recorded as two (side by side, before ladder_merge was widened): the most climbed takes the
        # others in. Returns whether any were joined
        merged = []
        for ladder in sorted(self.ladders, key=lambda r: -r["count"]):
            into = next((m for m in merged if continues(m, ladder["x"], ladder["top"], ladder["bottom"])), None)
            if into is None:
                merged.append(dict(ladder))
                continue
            total = into["count"] + ladder["count"]
            into["x"] = (into["x"] * into["count"] + ladder["x"] * ladder["count"]) / total
            into["top"], into["bottom"] = min(into["top"], ladder["top"]), max(into["bottom"], ladder["bottom"])
            into["count"] = total
        changed = len(merged) < len(self.ladders)
        self.ladders = merged
        return changed

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
            if sum(counts[p] for p in chain) < min_line_samples or (chain[-1][0] - chain[0][0] + 1) * bin_size < min_line_width:
                continue
            xy = np.array([((b + 0.5) * bin_size, y) for b, y in chain], dtype=np.float32)
            if len(xy) == 1:
                xy = np.array([[xy[0][0] - bin_size / 2, xy[0][1]], [xy[0][0] + bin_size / 2, xy[0][1]]], dtype=np.float32)
            lines.append([tuple(p) for p in cv2.approxPolyDP(xy.reshape(-1, 1, 2), 1.5, False).reshape(-1, 2)])
        return without_duplicates(lines)

    def on_ladder(self, x, y):  # Whether map (x, y) is part-way up a recorded rope (not at its top or bottom)
        return any(abs(ladder["x"] - x) <= on_rope_x and ladder["top"] + merge_height < y < ladder["bottom"] - merge_height
                   for ladder in self.confirmed_ladders())

    def confirmed_ladders(self):
        return [ladder for ladder in self.ladders if ladder["count"] >= min_ladder_count and ladder["bottom"] - ladder["top"] >= 10]

    def to_json(self):
        return {"ground": {str(b): column for b, column in self.ground.items()}, "ladders": self.ladders}

    @classmethod
    def from_json(cls, data):
        m = cls()
        m.ground = {int(b): [list(c) + [0.0] * (4 - len(c)) for c in column] for b, column in data.get("ground", {}).items()}  # Older files: no mob statistics
        for column in m.ground.values():  # Recordings made before heights were merged
            if consolidate(column):
                m.dirty = True
        m.ladders = [dict(ladder) for ladder in data.get("ladders", [])]
        if m.merge_ladders():
            m.dirty = True
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
        self.scroll = None  # ((x, y) px/s the camera is scrolling at, grab time of the frame it was measured on), for draw_shift
        self.held = deque()  # (time, x, y) ground readings waiting out ground_delay
        self.status = None  # Why nothing is being recorded or drawn yet, for the Debug panel; None once lined up with the map
        self.camera_resets = 0  # Times the camera tracking lost its place on this map (each starts the minimap samples again)

    def path(self, map_id=None):
        return os.path.join(folder, map_id or self.map_id, "platforms.json")

    def recorded(self, map_id):  # Whether anything is recorded on that map: its coords then depend on the map's saved minimap picture
        if map_id == self.map_id and self.platforms is not None:
            return bool(self.platforms.ground or self.platforms.ladders)
        return os.path.exists(self.path(map_id))

    def switch(self, map_id):  # Saves what was recorded on the old map and loads the new one's
        self.save()
        self.map_id = map_id
        self.camera.reset()
        self.movement.reset()
        self.held.clear()
        self.camera_resets = 0
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

    def update(self, frame, frame_rect, player_rect, minimap, now, record, mobs=None, erase=False):  # frame: PIL game area; rects in
        # screen coords; mobs: this frame's detected Mob rects, None when detection isn't running (nothing to learn from); erase: remove
        # what the player passes over instead of recording it
        if minimap is not None and minimap.map_id is not None and minimap.map_id != self.map_id:
            self.switch(minimap.map_id)
        self.track_scroll(self.camera.update(frame), now)
        self.frame_rect = frame_rect
        self.feet = None
        if self.calibration is None:
            return
        if self.camera.lost:  # Camera coords jumped: start following again
            self.movement.reset()
            self.calibration.reset()
            self.camera_resets += 1
        if player_rect is None:
            self.status = "player not found" if not self.calibration.anchored else None
            return
        cx, cy = self.camera.position
        position = (cx + (player_rect[0] + player_rect[2]) / 2 - frame_rect[0], cy + player_rect[3] - frame_rect[1])
        state = self.movement.update(now, *position)
        if minimap is not None and minimap.position is not None:
            self.calibration.add(position, minimap.position)
        if not self.calibration.anchored:
            self.status = self.startup_status(minimap)
            return
        self.status = None
        self.feet = self.calibration.to_map(position)
        if erase:  # Wherever the feet go, walking, jumping or falling: a scrap of ground in mid-air is cleaned up by jumping through it
            self.platforms.erase(*self.feet)
        elif record and state == movement.GROUND and self.movement.steady >= 3 and not self.platforms.on_ladder(*self.feet):
            self.held.append((now, *self.feet))  # Never part-way up a rope: that's not ground, however still the player is
        elif record and state == movement.LADDER and self.movement.steady >= 2:
            self.platforms.add_ladder(*self.feet)
        if not record or state != movement.GROUND:  # Off the ground: the last readings may already have been past the ledge, or rising
            self.held.clear()
        while self.held and now - self.held[0][0] >= ground_delay:
            self.platforms.add_ground(*self.held.popleft()[1:])
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

    def startup_status(self, minimap):  # What it's waiting for before it can line up with the map
        c = self.calibration
        if minimap is None or minimap.player is None:
            return "minimap dot not found"
        if minimap.position is None:
            return "finding this minimap view in the map's saved minimap"
        if c.scale is None:
            resets = ", camera lost %d times" % self.camera_resets if self.camera_resets else ""
            return "measuring minimap scale: dot moved %.0f of %d px, %d of %d readings%s (walk, climb or drop)" % (
                c.spread(), calibration_spread, len(c.samples), calibration_samples, resets)
        return "lining up with the minimap"

    def track_scroll(self, shift, now):  # How fast the camera is scrolling, smoothed over a few frames; still if it couldn't be measured
        last = self.scroll
        speed = (0.0, 0.0)
        if shift is not None and last is not None and now > last[1]:
            dt = now - last[1]
            (vx, vy), a = last[0], scroll_smoothing
            speed = (vx + a * (shift[0] / dt - vx), vy + a * (shift[1] / dt - vy))
        self.scroll = (speed, now)

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

    def to_screen(self, point, frame_rect, now=None):  # Map coords to screen coords, for drawing; None until anchored. now: draw where
        # it is at that time (see draw_shift), not where it was in the last frame
        shift = self.screen_shift(frame_rect) if now is None else self.draw_shift(frame_rect, now)
        return (point[0] + shift[0], point[1] + shift[1]) if shift is not None else None

    def draw_shift(self, frame_rect, now):  # screen_shift, moved on by how far the camera has scrolled since the frame it's from was
        # grabbed, at its recent speed. Drawn from frames 40-70 ms old, the map trailed the scrolling screen by that much
        shift, scroll = self.screen_shift(frame_rect), self.scroll
        if shift is None or scroll is None:
            return shift
        (vx, vy), grabbed = scroll
        age = min(max(now - grabbed, 0.0), max_predict)
        return shift[0] - vx * age, shift[1] - vy * age  # The scene moves the opposite way to the camera

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
