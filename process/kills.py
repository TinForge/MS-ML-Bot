# Tells kills from the EXP number on the status bar, which changes the moment a mob dies. The body then fades out for a while,
# which the detector can't tell from a live mob, so the mob attacked last is left out of targeting while it fades

import threading

from data import config

exp_wait = config.exp_wait  # Seconds after an attack's hit lands to watch for EXP going up before attacking the same mob again
dead_time = config.dead_time  # Seconds a killed mob's box is left out of targeting while it fades
kill_window = 2.0  # EXP changing this long after an attack counts as its kill; later, or with no attack, it's from something else
match_distance = 60  # How far (px) a fading mob's box may shift between frames (knockback, the camera scrolling) and still be it
read_timeout = 1.0  # Seconds without a readable EXP before the check stops being used (the bot falls back on gone_delay)


class KillCheck:  # Used from three threads: stats (read), bot (attacked) and calculations (alive)
    def __init__(self):
        self.lock = threading.Lock()
        self.exp = None  # Last EXP read
        self.read_at = None  # Grab time of the frame it was last read from
        self.changed_at = None  # Grab time of the frame EXP last changed in
        self.target = None  # (time, rect) of the last attack and the mob it was aimed at
        self.dead = []  # [rect, until] of killed mobs fading out; rect follows the box as it shifts

    def read(self, exp, when):  # Each status bar reading; exp None if unreadable (a misread is skipped, not taken as a change)
        if exp is None:
            return
        with self.lock:
            if self.exp is not None and exp != self.exp:  # Up on a kill (or reset by a level up, which is one too)
                self.changed_at = when
                if self.target is not None and 0 < when - self.target[0] <= kill_window:
                    self.dead.append([self.target[1], when + dead_time])
                    self.target = None
            self.exp, self.read_at = exp, when

    def usable(self, now):  # Whether EXP is being read, so kills can be told from it
        return self.read_at is not None and now - self.read_at < read_timeout

    def attacked(self, rect, when):  # Each attack, with the mob it was aimed at
        with self.lock:
            self.target = (when, rect)

    def alive(self, instances, now):  # Detections without the killed mobs still fading out: each takes the nearest mob box near it
        with self.lock:
            self.dead = [d for d in self.dead if d[1] > now]
            if not self.dead:
                return instances
            dropped = set()
            for spot in self.dead:
                rect = spot[0]
                near = [r for r in instances if r.name == "Mob" and id(r) not in dropped and abs(r.center_x - rect.center_x) <= match_distance
                        and abs(r.center_y - rect.center_y) <= match_distance]
                if near:
                    closest = min(near, key=lambda r: abs(r.center_x - rect.center_x) + abs(r.center_y - rect.center_y))
                    dropped.add(id(closest))
                    spot[0] = closest  # Followed from frame to frame
            return [r for r in instances if id(r) not in dropped]


instance = KillCheck()
