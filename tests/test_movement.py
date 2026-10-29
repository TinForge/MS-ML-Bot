# Tests for the movement state classifier, on made-up feet tracks (y grows downwards)

import unittest

from tools.movement import AIR, GROUND, LADDER, MovementState

GRAVITY = 2000  # px/s², roughly MapleStory's
JUMP_SPEED = 555  # px/s upwards at the start of a jump


def run(track, rate=18, state=None):  # track(t) -> (x, y); returns the states after each sample
    state = state or MovementState()
    return [state.update(i / rate, *track(i / rate)) for i in range(int(rate * 1.5))], state


class MovementTests(unittest.TestCase):
    def test_walking_flat_and_on_a_slope(self):
        states, _ = run(lambda t: (500 + 125 * t, 600))
        self.assertEqual(states[-1], GROUND)
        states, _ = run(lambda t: (500 + 125 * t, 600 - 0.5 * 125 * t))  # Uphill
        self.assertEqual(states[-1], GROUND)

    def test_standing_still(self):
        states, _ = run(lambda t: (500, 600))
        self.assertEqual(states[-1], GROUND)

    def test_jumping_is_air(self):
        jump = lambda t: (500 + 125 * t, 600 - JUMP_SPEED * t + GRAVITY * t * t / 2)  # Up and back down in ~0.55 s
        states = [s for s in states_during(jump, 0.55)]
        self.assertTrue(all(s == AIR for s in states))

    def test_falling_is_air(self):
        states, _ = run(lambda t: (500, 300 + GRAVITY * t * t / 2))
        self.assertEqual(states[5], AIR)

    def test_a_long_drop_is_not_a_climb(self):  # Full falling speed no longer speeds up: no gravity to see, but far too fast to climb
        fall = lambda t: (500, 300 + min(GRAVITY * t * t / 2, 670 * t - 670 ** 2 / (2 * GRAVITY)))  # Capped at 670 px/s after 0.33 s
        landed = 300 + 670 * 1.0 - 670 ** 2 / (2 * GRAVITY)  # Hits the ground 1 s in
        states, _ = run(lambda t: (500, min(fall(t)[1], landed)))
        self.assertNotIn(LADDER, states)
        self.assertEqual(states[-1], GROUND)  # Then standing where it landed, not hanging on a rope

    def test_climbing_and_hanging(self):
        climb = lambda t: (500, 600 - 100 * t)
        states, state = run(climb)
        self.assertEqual(states[-1], LADDER)
        hang = run(lambda t: (500, 450), state=state)[0]  # Stops halfway up
        self.assertEqual(hang[-1], LADDER)  # Still in mid-air: hanging, not standing

    def test_slow_climbing_stays_on_the_rope(self):  # Easing to a stop on a rope used to read as ground, and recorded platform slivers
        state, rate = MovementState(), 18
        follow = lambda start, end, track: [state.update(t, *track(t)) for t in (i / rate for i in range(int(start * rate), int(end * rate)))]
        self.assertEqual(follow(0, 1.5, lambda t: (500, 600 - 100 * t))[-1], LADDER)  # Climbing to 450
        slow = follow(1.5, 3, lambda t: (500, 450 - 12 * (t - 1.5)))  # 12 px/s: below climb_speed, but not still
        self.assertTrue(all(s == LADDER for s in slow))
        off = follow(3, 4, lambda t: (500 + 125 * (t - 3), 432))  # Stepping off sideways at the top
        self.assertEqual(off[-1], GROUND)

    def test_sideways_speed(self):
        _, state = run(lambda t: (500 - 125 * t, 600))
        self.assertAlmostEqual(state.vx, -125, delta=5)
        _, state = run(lambda t: (500, 600))
        self.assertEqual(state.vx, 0)

    def test_slow_sampling(self):  # With detection off and the player box hidden, reads come 4 times a second
        states, _ = run(lambda t: (500 + 125 * t, 600), rate=4)
        self.assertEqual(states[-1], GROUND)
        states, _ = run(lambda t: (500, 600 - 100 * t), rate=4)
        self.assertEqual(states[-1], LADDER)

    def test_tracking_noise(self):
        noise = [0, 1, -1, 1, 0, -1, 1, 0, -1, 0, 1, -1, 0, 1, 0, -1, 1, 0, 0, 1, -1, 0, 1, 0, -1, 0, 1]
        states, _ = run(lambda t: (500 + 125 * t, 600 + noise[int(round(t * 18))]))
        self.assertEqual(states[-1], GROUND)


def states_during(track, duration, rate=30):  # States during a short movement, after enough samples to judge
    state = MovementState()
    out = [state.update(i / rate, *track(i / rate)) for i in range(int(rate * duration))]
    return out[3:]


if __name__ == "__main__":
    unittest.main()
