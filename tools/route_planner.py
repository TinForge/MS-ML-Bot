# Plans routes across a recorded map (tools/map_recorder.py), in map coords. The platforms are the places; the ways between them are
# dropping down, jumping up or across, and climbing a recorded rope. Each costs a rough travel time, and Dijkstra finds the quickest
# route. The bot follows only the route's first hop and plans again, so it adapts as it goes

import heapq
from dataclasses import dataclass

import numpy as np

step = 8  # Map pixels between the points platforms are compared at
stand_margin = 30  # Feet within this of a platform's height are standing on it
walk_speed = 125.0  # Map px/s walking
climb_speed = 100.0  # Map px/s climbing a rope
drop_time = 0.7  # Seconds for a drop: down-jump, fall, land
jump_time = 0.9  # Seconds for a jump up or across: lining up, jumping, landing
rope_time = 0.8  # Seconds getting onto a rope and off at the top, besides climbing
jump_reach = 60  # How far past a platform's end a jump reaches sideways
fall_reach = 60  # How far past a platform's end lower ground makes that end a ledge (a knockback over it lands there)
rope_x = 12  # How far from a rope's line it can be grabbed from
rope_edge = 40  # Ropes usually hang just past a platform's edge: platforms ending this close beside one count as at its ends
walk_gap = 24  # Platform pieces whose ends are this close, at about the same height, are one platform recorded in pieces
walk_step = 12  # ... the most their heights may differ at the join (a real step, like a stair, needs a jump)
rope_extra_reach = 30  # A rope is grabbed a little higher than a platform is jumped onto (hands are above the feet, and its recorded
# bottom is only as low as it was ever climbed)


@dataclass
class Hop:  # One way off a platform
    kind: str  # drop, jump or rope
    to: int  # Index of the platform it leads to
    x1: float  # Where on the platform it leaves from, in map x
    x2: float
    ladder: int = None  # rope: index into the ladders
    cost: float = 0  # Seconds, besides walking to it

    def leave_at(self, x):  # The nearest point to x it can be taken from
        return min(max(x, self.x1), self.x2)


class RoutePlanner:
    def __init__(self, lines, ladders, jump_height):  # lines: platforms as [(x, y), ...]; ladders: {"x", "top", "bottom"} dicts
        self.lines, self.ladders, self.jump_height = lines, ladders, jump_height
        self.hops = [[] for _ in lines]  # Per platform, the ways off it
        if not lines:
            return
        x_min = min(p[0] for line in lines for p in line) - jump_reach
        x_max = max(p[0] for line in lines for p in line) + jump_reach
        self.grid = np.arange(x_min, x_max + step, step)
        self.tops = np.full((len(lines), len(self.grid)), np.nan)  # Each platform's height at each grid point, NaN off it
        reach = np.full_like(self.tops, np.nan)  # The same, held level up to jump_reach past its ends: where a jump lands on it
        self.beside = np.full_like(self.tops, np.nan)  # The same, up to rope_edge past its ends: ropes hanging by its edge
        for i, line in enumerate(lines):
            xs, ys = [p[0] for p in line], [p[1] for p in line]
            for heights, margin in ((self.tops, 0), (reach, jump_reach), (self.beside, rope_edge)):
                within = (self.grid >= xs[0] - margin) & (self.grid <= xs[-1] + margin)
                heights[i, within] = np.interp(self.grid[within], xs, ys)
        self.group = list(range(len(lines)))  # Pieces walked across as one platform share a group (see add_walks)
        self.add_walks()
        for a in range(len(lines)):
            self.add_drops(a)
            self.add_jumps(a, reach)
        self.add_ropes()

    # --- Building the hops ---

    def intervals(self, mask):  # Runs of True in a grid mask, as (x1, x2)
        if not mask.any():
            return []
        edges = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
        starts, ends = np.flatnonzero(edges == 1), np.flatnonzero(edges == -1) - 1
        return [(float(self.grid[s]), float(self.grid[e])) for s, e in zip(starts, ends)]

    def add_walks(self):  # One platform recorded in pieces (a gap in the recording, a bump): walk from one to the next
        ends = [((line[0][0], line[0][1]), (line[-1][0], line[-1][1])) for line in self.lines]
        for a, (_, (ax, ay)) in enumerate(ends):  # a's right end
            for c, ((cx, cy), _) in enumerate(ends):  # c's left end
                if c != a and -walk_gap <= cx - ax <= walk_gap and abs(cy - ay) <= walk_step:
                    self.hops[a].append(Hop("walk", c, ax, ax))
                    self.hops[c].append(Hop("walk", a, cx, cx))
                    self.join(a, c)
        for a in range(len(self.lines)):  # The same ground recorded twice, overlapping a few pixels apart
            with np.errstate(invalid="ignore"):
                same = np.abs(self.tops - self.tops[a]) <= walk_step
            same[a] = False
            for c in np.flatnonzero(same.any(axis=1)).tolist():
                for x1, x2 in self.intervals(same[c]):
                    self.hops[a].append(Hop("walk", c, x1, x2))
                self.join(a, c)

    def join(self, a, c):
        old, new = self.group[c], self.group[a]
        self.group = [new if g == old else g for g in self.group]

    def same_platform(self, a, c):  # Pieces of one platform: the bot just walks between them
        return self.group[a] == self.group[c]

    def width(self, a):  # Width of the whole platform a is a piece of
        pieces = [self.lines[i] for i in range(len(self.lines)) if self.group[i] == self.group[a]]
        return max(p[-1][0] for p in pieces) - min(p[0][0] for p in pieces)

    def ledges(self, a, x):  # Distances from map x to the ends of the platform a is a piece of, (left, right), each None where the
        # end isn't a ledge: no lower ground recorded just past it, as at a wall or the bottom of the map
        pieces = [i for i in range(len(self.lines)) if self.group[i] == self.group[a]]
        lx, ly = min((self.lines[i][0] for i in pieces), key=lambda p: p[0])
        rx, ry = max((self.lines[i][-1] for i in pieces), key=lambda p: p[0])
        return (x - lx if self.ground_below(lx, ly, -1) else None, rx - x if self.ground_below(rx, ry, 1) else None)

    def ground_below(self, x, y, side):  # Whether a platform lower than y lies within fall_reach past x (side -1: left, 1: right)
        past = (self.grid - x) * side
        within = (past > 0) & (past <= fall_reach)
        with np.errstate(invalid="ignore"):
            return bool((self.tops[:, within] > y + stand_margin).any())

    def add_drops(self, a):  # Dropping from a lands on the highest platform below it there
        here = self.tops[a]
        with np.errstate(invalid="ignore"):
            below = np.where(self.tops > here + stand_margin, self.tops, np.inf)
        lands = np.argmin(below, axis=0)
        found = np.isfinite(below.min(axis=0)) & ~np.isnan(here)
        for b in set(lands[found].tolist()):
            for x1, x2 in self.intervals(found & (lands == b)):
                self.hops[a].append(Hop("drop", b, x1, x2, cost=drop_time))

    def add_jumps(self, a, reach):  # Jumping lands on a platform up to jump_height above, or across a gap at about the same height
        here = self.tops[a]
        with np.errstate(invalid="ignore"):
            rise = here[None, :] - reach  # How far above the feet each platform is where a jump would land on it
            up = (rise > stand_margin) & (rise <= self.jump_height)
            across = (np.abs(rise) <= stand_margin) & np.isnan(self.tops)  # A gap: beside a, not under the feet
        able = (up | across) & ~np.isnan(here)[None, :]
        able[a] = False
        for c in np.flatnonzero(able.any(axis=1)).tolist():
            if self.same_platform(a, c):  # Walked between, not jumped
                continue
            for x1, x2 in self.intervals(able[c]):
                self.hops[a].append(Hop("jump", c, x1, x2, cost=jump_time))

    def add_ropes(self):  # A rope leads from a platform it can be grabbed from to the one at its top
        for j, ladder in enumerate(self.ladders):
            column = int(round((ladder["x"] - self.grid[0]) / step))
            if not 0 <= column < len(self.grid):
                continue
            tops = self.beside[:, column]  # Platforms at the rope, or ending just beside it
            for a in np.flatnonzero(~np.isnan(tops)).tolist():
                ground = tops[a]
                if not (ground - ladder["bottom"] <= self.jump_height + rope_extra_reach and ladder["top"] < ground - stand_margin):
                    continue  # Its bottom is out of reach from here, or it doesn't lead up
                with np.errstate(invalid="ignore"):
                    ends = [c for c in np.flatnonzero(np.abs(tops - ladder["top"]) <= stand_margin).tolist() if c != a]
                if ends:
                    c = min(ends, key=lambda c: abs(tops[c] - ladder["top"]))
                    climb = (ladder["bottom"] - ladder["top"]) / climb_speed
                    self.hops[a].append(Hop("rope", c, ladder["x"] - rope_x, ladder["x"] + rope_x, ladder=j, cost=rope_time + climb))

    # --- Where the player is, and routes ---

    def line_at(self, x, y):  # The platform under feet at map (x, y), or None
        column = int(round((x - self.grid[0]) / step)) if self.lines else -1
        if not 0 <= column < len(self.grid):
            return None
        tops = self.tops[:, column]
        with np.errstate(invalid="ignore"):
            close = np.flatnonzero(np.abs(tops - y) <= stand_margin)
        return int(min(close, key=lambda i: abs(tops[i] - y))) if len(close) else None

    def routes(self, start, x, avoid=()):  # Quickest routes from map x on platform start to every platform it can reach:
        # {platform: (seconds, [hops])}. avoid: platforms not to jump onto (jumps at them kept failing)
        best = {start: (0.0, [])}
        queue = [(0.0, start, x, [])]
        done = set()
        while queue:
            cost, here, at, path = heapq.heappop(queue)
            if here in done:
                continue
            done.add(here)
            for hop in self.hops[here]:
                if hop.kind == "jump" and hop.to in avoid:
                    continue
                leave = hop.leave_at(at)
                total = cost + abs(leave - at) / walk_speed + hop.cost
                if hop.to not in best or total < best[hop.to][0]:
                    arrive = self.ladders[hop.ladder]["x"] if hop.kind == "rope" else leave
                    best[hop.to] = (total, path + [hop])
                    heapq.heappush(queue, (total, hop.to, arrive, path + [hop]))
        return best

    def height(self, line, x):  # The platform's height at map x, held level past its ends
        points = self.lines[line]
        return float(np.interp(x, [p[0] for p in points], [p[1] for p in points]))

    def path(self, start, x, hops):  # The route as map points to draw: from the feet, where each hop leaves and lands (a rope's foot
        # and top), to where the last one lands
        points, line = [(x, self.height(start, x))], start
        for hop in hops:
            leave = hop.leave_at(x)
            points.append((leave, self.height(line, leave)))
            if hop.kind == "rope":
                ladder = self.ladders[hop.ladder]
                x = ladder["x"]
                points += [(x, ladder["bottom"]), (x, ladder["top"])]
            else:
                ends = self.lines[hop.to]
                x = min(max(leave, ends[0][0]), ends[-1][0])  # A drop lands straight below; a jump on the nearest bit of the platform
            points.append((x, self.height(hop.to, x)))
            line = hop.to
        return points

    def route(self, start, x, goal, avoid=()):  # The hops from platform start to platform goal, quickest first; None if no way there
        found = self.routes(start, x, avoid).get(goal)
        return found[1] if found is not None else None
