# Tests for carrying on from where the player was last seen while their nametag is covered

import unittest
from unittest import mock

from data import values
from process import calculations


class LostPlayerTests(unittest.TestCase):
    def setUp(self):
        self.thread = calculations.CalculationThread()

    def find(self, rect):
        with mock.patch.object(values, "player_rect", rect):
            player = self.thread.find_player([])
        return (player.x1, player.y1, player.x2, player.y2) if player is not None else None

    def test_carries_on_from_where_it_was_last_seen(self):
        self.assertEqual(self.find((500, 300, 550, 366)), (500, 300, 550, 366))
        for _ in range(100):  # However long the nametag stays covered
            self.assertEqual(self.find(None), (500, 300, 550, 366))

    def test_found_again_takes_over(self):
        self.find((500, 300, 550, 366))
        self.find(None)
        self.assertEqual(self.find((520, 300, 570, 366)), (520, 300, 570, 366))
        self.assertEqual(self.find(None), (520, 300, 570, 366))

    def test_never_seen(self):
        self.assertIsNone(self.find(None))


class HiddenJiggleTests(unittest.TestCase):  # Nametag missing and nothing to do: walk back and forth until it's found
    def setUp(self):
        from data import profiles
        from process import behaviours
        from tests.test_behaviours import FIXTURES
        patcher = mock.patch.object(profiles, "folder", FIXTURES)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.behaviours = behaviours
        self.b = behaviours.for_profile(profiles.load("swordsman"))

    def decide(self, now, hidden=True, state=None):
        from process.behaviours import Situation
        return self.b.decide(Situation(state=state, now=now, player_hidden=hidden))

    def test_jiggles_after_two_seconds_hidden_and_idle(self):
        self.assertEqual(self.decide(10.0).kind, "wait")
        self.assertEqual(self.decide(11.9).kind, "wait")
        first = self.decide(12.1)
        self.assertEqual((first.kind, first.label), ("move", "nametag hidden: jiggling"))
        later = self.decide(12.1 + self.behaviours.jiggle_step + 0.05)
        self.assertNotEqual(later.direction, first.direction)  # Back the other way

    def test_found_again_stops_it(self):
        self.decide(10.0)
        self.decide(12.1)
        self.assertEqual(self.decide(12.2, hidden=False).kind, "wait")
        self.assertEqual(self.decide(12.3).kind, "wait")  # Hidden again: two more seconds first

    def test_something_to_do_comes_first(self):  # Climbing with the nametag behind the rope, say
        from process.behaviours import Situation
        self.decide(10.0)
        climbing = self.b.decide(Situation(state="Navigate", route="climb", now=12.5, player_hidden=True))
        self.assertEqual(climbing.kind, "climb")


if __name__ == "__main__":
    unittest.main()
