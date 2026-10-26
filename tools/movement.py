# Classifies how the player is moving from their feet positions over time: on the ground, on a ladder, or in the air

from collections import deque

import numpy as np

GROUND, LADDER, AIR = "Ground", "Ladder", "Air"

window_time = 0.25  # Seconds of recent feet positions looked at (at least min_samples, however long that takes)
min_samples = 3
still_distance = 3  # Pixels moved across the window that still count as not moving (tracking noise)
max_acceleration = 700  # px/s² of vertical acceleration allowed; gravity (~2000) is far above, walking and climbing have none
max_slope = 1.0  # Steepest slope walked on, as height per width
ladder_drift = 15  # px/s of sideways speed allowed while climbing
climb_speed = 30  # px/s of vertical speed that counts as climbing rather than standing


class MovementState:
    def __init__(self):
        self.history = deque(maxlen=60)  # (time, x, y) of the feet in map coords
        self.state = None
        self.steady = 0  # Consecutive updates in the current state
        self.vx = None  # Sideways speed in px/s over the recent window (negative: left), None until there are enough samples

    def reset(self):
        self.history.clear()
        self.state = None
        self.steady = 0
        self.vx = None

    def update(self, t, x, y):  # Returns Ground, Ladder, Air, or None while there aren't enough samples yet
        if self.history and t <= self.history[-1][0]:
            return self.state
        self.history.append((t, x, y))
        state = self.classify()
        self.steady = self.steady + 1 if state == self.state else 1
        self.state = state
        return state

    def classify(self):
        recent = [s for s in self.history if s[0] >= self.history[-1][0] - window_time]
        if len(recent) < min_samples:
            recent = list(self.history)[-min_samples:]
        if len(recent) < min_samples:
            return None
        t, x, y = (np.array(v, dtype=float) for v in zip(*recent))
        t -= t[0]
        if np.ptp(x) <= still_distance and np.ptp(y) <= still_distance:
            self.vx = 0.0
            return self.state if self.state in (GROUND, LADDER) else GROUND  # Standing, or hanging on a ladder
        acceleration = 2 * np.polyfit(t, y, 2)[0]
        if abs(acceleration) > max_acceleration:  # The path bends: gravity
            return AIR
        vx, vy = np.polyfit(t, x, 1)[0], np.polyfit(t, y, 1)[0]
        self.vx = float(vx)
        if abs(vx) < ladder_drift and abs(vy) >= climb_speed:
            return LADDER
        if self.state == LADDER and abs(vx) < ladder_drift:  # Climbing slowly or easing to a stop is still on the rope: only stepping
            return LADDER  # off sideways or jumping (the acceleration above) leaves it. Taken for ground, it recorded slivers of "platform"
        if abs(vy) <= max(20, max_slope * abs(vx)):
            return GROUND
        return AIR
