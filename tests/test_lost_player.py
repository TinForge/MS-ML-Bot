# Tests for carrying on from where the player was last seen while their nametag is covered

import unittest
from unittest import mock

from data import config, values
from process import calculations


class LostPlayerTests(unittest.TestCase):
    def setUp(self):
        self.thread = calculations.CalculationThread()
        self.clock = [100.0]
        patcher = mock.patch.object(calculations.time, "time", lambda: self.clock[0])
        patcher.start()
        self.addCleanup(patcher.stop)

    def find(self, rect, at):
        self.clock[0] = 100.0 + at
        with mock.patch.object(values, "player_rect", rect):
            player = self.thread.find_player([])
        return (player.x1, player.y1, player.x2, player.y2) if player is not None else None

    def test_carries_on_from_where_it_was_last_seen(self):
        self.assertEqual(self.find((500, 300, 550, 366), 0), (500, 300, 550, 366))
        self.assertEqual(self.find(None, config.lost_grace - 0.1), (500, 300, 550, 366))  # Nametag covered: still there
        self.assertIsNone(self.find(None, config.lost_grace + 0.1))  # Too long: lost, stop and search

    def test_found_again_takes_over(self):
        self.find((500, 300, 550, 366), 0)
        self.find(None, 0.3)
        self.assertEqual(self.find((520, 300, 570, 366), 0.5), (520, 300, 570, 366))
        self.assertEqual(self.find(None, 0.5 + config.lost_grace - 0.1), (520, 300, 570, 366))  # Counted from the new sighting

    def test_never_seen(self):
        self.assertIsNone(self.find(None, 0))


if __name__ == "__main__":
    unittest.main()
