# Tests for EXP Kill Check: reading EXP from the status bar, telling kills from it, and the attack pacing that uses it

import unittest
from unittest import mock

import numpy as np

from data import profiles, rects
from process import behaviours, kills
from process.behaviours import Situation
from tools import stat_reader
from tests.test_behaviours import FIXTURES


def setUpModule():  # Fixed copies of the profiles, as in test_behaviours
    patcher = mock.patch.object(profiles, "folder", FIXTURES)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def status_bar(text_after_mp):  # A text mask like the status bar's: the MP label, then text in the value font
    height = stat_reader.label_masks['MP'].shape[0]
    mask = np.zeros((20, 400), bool)
    label = stat_reader.label_masks['MP'] > 0
    mask[5:5 + height, 10:10 + label.shape[1]] = label
    x = 10 + label.shape[1] + 2
    for ch in text_after_mp:
        if ch == ' ':
            x += 4
            continue
        glyph = stat_reader.font_masks[ch] if ch in stat_reader.font_masks else np.ones((height, 7), bool)  # '#': a label letter
        top = 5 + height - 2 - glyph.shape[0] if ch in ',.' else 5 + 1  # Digits sit on the label's rows; , and . at the bottom
        if ch == ',':
            top += 1
        mask[top:top + glyph.shape[0], x:x + glyph.shape[1]] = glyph
        x += glyph.shape[1] + 1
    return mask


def mob(x, y=500):
    return rects.Rect("Mob", "red", x - 20, y - 40, x + 20, y, 0.9)


class ReadExpTests(unittest.TestCase):
    def test_reads_exp_after_mp(self):
        self.assertEqual(stat_reader.read_exp(status_bar("[291/311]      ## # .316[5.79%]")), (316, 5.79))

    def test_thousands(self):
        self.assertEqual(stat_reader.read_exp(status_bar("[305/311]      ## # 1,440[26.37%]")), (1440, 26.37))

    def test_unreadable(self):
        self.assertIsNone(stat_reader.read_exp(status_bar("[305/311]      ## # 1,440[26.37")))  # Cut off
        self.assertIsNone(stat_reader.read_exp(np.zeros((20, 400), bool)))  # No status bar


class KillCheckTests(unittest.TestCase):
    def setUp(self):
        self.check = kills.KillCheck()
        self.check.read(100, 9.0)

    def test_exp_rising_after_an_attack_kills_its_mob(self):
        target, other = mob(300), mob(600)
        self.check.attacked(target, 10.0)
        self.check.read(100, 10.1)
        self.assertEqual(self.check.alive([target, other], 10.1), [target, other])  # No change yet
        self.check.read(112, 10.25)
        self.assertEqual(self.check.changed_at, 10.25)
        self.assertEqual(self.check.alive([target, other], 10.3), [other])  # Fading out: left out
        self.assertEqual(self.check.alive([target, other], 10.25 + kills.dead_time + 0.01), [target, other])  # Gone by then

    def test_follows_the_fading_box(self):  # The camera scrolls while it fades
        self.check.attacked(mob(300), 10.0)
        self.check.read(112, 10.2)
        for i, x in enumerate((330, 360, 390)):
            shifted = mob(x)
            self.assertEqual(self.check.alive([shifted], 10.3 + i * 0.03), [])

    def test_only_the_nearest_box_is_left_out(self):  # A live mob walking over the body is still a target
        dead, live = mob(300), mob(340)
        self.check.attacked(dead, 10.0)
        self.check.read(112, 10.2)
        self.assertEqual(self.check.alive([live, dead], 10.3), [live])

    def test_exp_change_without_a_recent_attack_kills_nothing(self):  # A quest, or long after the attack
        target = mob(300)
        self.check.attacked(target, 10.0)
        self.check.read(112, 10.0 + kills.kill_window + 0.5)
        self.assertEqual(self.check.alive([target], 13.0), [target])

    def test_misreads_are_skipped(self):
        self.check.read(None, 10.0)
        self.check.read(100, 10.1)
        self.assertIsNone(self.check.changed_at)
        self.assertTrue(self.check.usable(10.5))
        self.assertFalse(self.check.usable(10.1 + kills.read_timeout + 0.1))  # Not read for a while: not used


class PacingTests(unittest.TestCase):  # With EXP Kill Check: no gone_delay, just long enough to see whether EXP went up
    def setUp(self):
        self.behaviour = behaviours.for_profile(profiles.load("swordsman"))
        self.basic = self.behaviour.profile.attack_named("Basic attack")
        self.behaviour.last_target = (10.0, 50, 0)  # Attacked this mob at 10.0
        self.landed = 10.0 + self.basic.hit_time

    def decide(self, seen, dx=50, killed_at=None):
        return self.behaviour.decide(Situation(state="Attack", dx=dx, dy=0, now=seen + 0.03, attack_last_used={"Basic attack": 10.0},
                                               target_seen=seen, kill_check=True, killed_at=killed_at))

    def test_alive_attacks_again_right_after_the_hit(self):
        self.assertEqual(self.decide(self.landed - 0.05).label, "waiting for the hit to land")
        self.assertEqual(self.decide(self.landed + 0.01).label, "checking EXP")
        self.assertEqual(self.decide(self.landed + kills.exp_wait + 0.01).kind, "attack")
        self.assertLess(kills.exp_wait, self.behaviour.profile.gone_delay + 0.01)

    def test_killed_mob_is_not_hit_again(self):
        for seen in (self.landed + 0.01, self.landed + 0.5):
            a = self.decide(seen, killed_at=self.landed)
            self.assertEqual((a.kind, a.label), ("stop", "killed: moving on"))

    def test_next_mob_attacked_straight_away(self):  # No waiting after a kill
        self.assertEqual(self.decide(self.landed + 0.01, dx=-50, killed_at=self.landed).kind, "attack")

    def test_exp_from_before_the_attack_is_not_a_kill(self):
        self.assertEqual(self.decide(self.landed + 0.01, killed_at=9.9).label, "checking EXP")

    def test_without_the_check_gone_delay_applies(self):
        a = self.behaviour.decide(Situation(state="Attack", dx=50, now=self.landed + 0.2, attack_last_used={"Basic attack": 10.0},
                                            target_seen=self.landed + 0.15, kill_check=False, killed_at=self.landed))
        self.assertEqual(a.label, "checking the mob is gone")


if __name__ == "__main__":
    unittest.main()
