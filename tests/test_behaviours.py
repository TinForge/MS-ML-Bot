# Tests for bot profiles, behaviours and the executor. Run from the repository root:
#   .venv\Scripts\python.exe -m unittest discover -s tests -t .

import os
import unittest
from unittest import mock

from data import profiles, values
from process import behaviours, executor
from process.behaviours import Situation
from tools import keyboard

SHIPPED = profiles.folder
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "profiles")  # Fixed copies: editing your profiles
# (keys, names, timings) never breaks these tests


def setUpModule():
    patcher = mock.patch.object(profiles, "folder", FIXTURES)
    patcher.start()
    unittest.addModuleCleanup(patcher.stop)


def decide(profile_name, **situation):
    profile = profiles.load(profile_name)
    return behaviours.for_profile(profile).decide(Situation(**situation))


class ProfileTests(unittest.TestCase):
    def test_shipped_profiles_load(self):  # Your real profiles, as edited
        with mock.patch.object(profiles, "folder", SHIPPED):
            self.check_all_load()
        self.check_all_load()  # And the test copies

    def check_all_load(self):
        names = profiles.available()
        self.assertTrue({"spearman", "swordsman", "hunter", "assassin"} <= set(names))
        for name in names:
            profiles.load(name)

    def test_spearman_matches_old_warrior_long(self):
        p = profiles.load("spearman")
        self.assertEqual((p.min_range, p.max_range), (45, 125))  # Old centre distances, less half a mob's width
        self.assertEqual(p.attacks[0].range_y, (-30, 75))
        self.assertEqual((p.platform_range, p.platform_height), (50, 100))

    def check_invalid(self, data, message):
        with self.assertRaises(profiles.ProfileError) as e:
            profiles.from_dict("test", data)
        self.assertIn(message, str(e.exception))

    def test_invalid_profiles_are_reported(self):
        attack = {"key": "Ctrl", "range_x": [0, 100], "range_y": [-10, 10]}
        self.check_invalid({"attacks": [dict(attack, key="Ctlr")]}, "not a known key")
        self.check_invalid({"attacks": [dict(attack, range_x=[100, 0])]}, "range_x must be [min, max]")
        self.check_invalid({"behaviour": "summoner", "attacks": [attack]}, "behaviour must be one of")
        self.check_invalid({}, "at least one enabled [[attacks]]")
        self.check_invalid({"attacks": [attack], "mobility": [{"type": "dash"}]}, "needs a key")
        self.check_invalid({"attacks": [attack], "keys": {"jump": "Altt"}}, "not a known key")
        profiles.from_dict("test", {"attacks": [attack], "mobility": [{"type": "flash_jump"}]})  # Uses the jump key

    def test_disabled_attacks_are_left_out_but_still_checked(self):
        attack = {"key": "Ctrl", "range_x": [0, 100], "range_y": [-10, 10]}
        p = profiles.from_dict("test", {"attacks": [dict(attack, name="Power", key="A", enabled=False), dict(attack, name="Basic")]})
        self.assertEqual([a.name for a in p.attacks], ["Basic"])
        self.check_invalid({"attacks": [dict(attack, key="Ctlr", enabled=False), attack]}, "not a known key")
        self.check_invalid({"attacks": [dict(attack, enabled=False)]}, "at least one enabled")

    def test_missing_profile(self):
        with self.assertRaises(profiles.ProfileError):
            profiles.load("does_not_exist")

    def test_attack_priority_and_cooldown(self):
        p = profiles.load("hunter")
        self.assertEqual(p.attack_for(200, 0).name, "Arrow Bomb")  # Listed first
        self.assertEqual(p.attack_for(200, 0, {"Arrow Bomb": 10.0}, now=11.0).name, "Basic shot")  # On cooldown
        self.assertEqual(p.attack_for(200, 0, {"Arrow Bomb": 10.0}, now=12.0).name, "Arrow Bomb")  # Ready again
        self.assertEqual(p.attack_for(365, 0).name, "Basic shot")  # Only it reaches that far

    def test_mobility_picks_longest_applicable(self):
        p = profiles.from_dict("test", {"attacks": [{"key": "Ctrl", "range_x": [0, 100], "range_y": [0, 0]}],
                                        "mobility": [{"type": "dash", "key": "Shift", "min_distance": 300},
                                                     {"type": "teleport", "key": "X", "min_distance": 500}]})
        self.assertIsNone(p.mobility_for(200))
        self.assertEqual(p.mobility_for(400).type, "dash")
        self.assertEqual(p.mobility_for(600).type, "teleport")


class MeleeTests(unittest.TestCase):
    def test_far_mob_uses_dash(self):
        a = decide("spearman", state="Attack", dx=400, randomizer=True)
        self.assertEqual((a.kind, a.mobility.type, a.direction), ("mobility", "dash", "right"))

    def test_moves_closer(self):
        self.assertEqual((decide("spearman", state="Attack", dx=200).kind, decide("spearman", state="Attack", dx=-200).direction), ("move", "left"))

    def test_attacks_in_range(self):
        a = decide("spearman", state="Attack", dx=-100, dy=0)
        self.assertEqual((a.kind, a.direction, a.attack.name), ("attack", "left", "Basic attack"))

    def test_jump_attacks_mob_slightly_above(self):
        self.assertEqual(decide("spearman", state="Attack", dx=100, dy=100).kind, "jump_attack")
        self.assertEqual(decide("swordsman", state="Attack", dx=50, dy=50).kind, "jump_attack")

    def test_stops_when_mob_out_of_vertical_reach(self):
        self.assertEqual(decide("spearman", state="Attack", dx=100, dy=200).kind, "stop")

    def test_too_close_steps_back(self):  # Unreachable before: the in-range check ran first
        a = decide("spearman", state="Attack", dx=30, dy=0)
        self.assertEqual((a.kind, a.direction, a.label), ("move", "left", "move away"))


class AttackPacingTests(unittest.TestCase):  # After a hit lands, gone_delay more; then attack again only if the mob is still there
    def setUp(self):
        self.profile = profiles.load("swordsman")
        self.basic = self.profile.attack_named("Basic attack")
        self.landed = 10.0 + self.basic.hit_time  # Basic attack pressed at 10.0

    def decide(self, seen, now=None):
        return behaviours.for_profile(self.profile).decide(Situation(state="Attack", dx=50, dy=0, now=seen + 0.03 if now is None else now,
                                                                     attack_last_used={"Basic attack": 10.0}, target_seen=seen))

    def test_first_attack_right_away(self):
        self.assertEqual(decide("swordsman", state="Attack", dx=50, dy=0, now=10.0, target_seen=9.98).kind, "attack")

    def test_waits_for_the_hit_to_land(self):  # Until then a frame shows the mob as it was before the hit
        a = self.decide(self.landed - 0.05)
        self.assertEqual((a.kind, a.label), ("stop", "waiting for the hit to land"))  # Stop, not wait: a held arrow key would keep walking

    def test_watches_gone_delay_then_attacks_if_still_there(self):  # A dead mob fades out meanwhile
        self.assertEqual(self.decide(self.landed + 0.01).label, "checking the mob is gone")
        self.assertEqual(self.decide(self.landed + self.profile.gone_delay + 0.01).kind, "attack")

    def test_each_attack_has_its_own_hit_time(self):
        attack = {"range_x": [0, 100], "range_y": [-10, 10]}
        p = profiles.from_dict("test", {"gone_delay": 0, "attacks": [dict(attack, name="Slow", key="A", hit_time=0.6),
                                                                     dict(attack, name="Fast", key="Ctrl", hit_time=0.2)]})
        situation = lambda last: Situation(state="Attack", dx=50, now=10.45, attack_last_used={last: 10.0}, target_seen=10.4)
        self.assertEqual(behaviours.for_profile(p).decide(situation("Slow")).label, "waiting for the hit to land")
        self.assertEqual(behaviours.for_profile(p).decide(situation("Fast")).kind, "attack")

    def test_profile_settings(self):
        attack = {"key": "Ctrl", "range_x": [0, 100], "range_y": [-10, 10]}
        p = profiles.from_dict("test", {"attacks": [attack]})
        self.assertEqual((p.attacks[0].hit_time, p.gone_delay), (0.35, 0.5))  # Defaults
        p = profiles.from_dict("test", {"gone_delay": 0.8, "attacks": [dict(attack, hit_time=0.25)]})
        self.assertEqual((p.attacks[0].hit_time, p.gone_delay), (0.25, 0.8))
        with self.assertRaises(profiles.ProfileError) as e:
            profiles.from_dict("test", {"attack_delay": 0.3, "attacks": [attack]})
        self.assertIn("replaced by hit_time", str(e.exception))


class AttackChoiceTests(unittest.TestCase):  # The swordsman profile: mobbing attack on groups, power attack to open, basic otherwise
    def setUp(self):
        self.behaviour = behaviours.for_profile(profiles.load("swordsman"))
        self.used = {}
        self.step = self.behaviour.profile.attack_named("Basic attack").hit_time + self.behaviour.profile.gone_delay + 0.05  # Between attacks

    def attack(self, now, dx=50, crowd=None):  # Decides as the bot loop would, recording the attack as the executor does
        a = self.behaviour.decide(Situation(state="Attack", dx=dx, dy=0, now=now, attack_last_used=self.used, target_seen=now, crowd=crowd))
        if a.attack is not None:
            self.used[a.attack.name] = now
        return a.attack.name if a.attack is not None else a.label

    def test_power_attack_opens_then_basic(self):
        hits = [self.attack(10.0 + i * self.step, dx=50 + i * 5) for i in range(3)]  # Knocked back a little each hit: the same mob
        self.assertEqual(hits, ["Power attack", "Basic attack", "Basic attack"])
        self.assertEqual(self.attack(10.0 + 3 * self.step, dx=-50), "Power attack")  # The other side: a new mob

    def test_opener_option_still_works(self):  # Only the first hit on each mob
        attack = {"key": "Ctrl", "range_x": [0, 100], "range_y": [-10, 10]}
        behaviour = behaviours.for_profile(profiles.from_dict("test", {"attacks": [dict(attack, name="Opener", key="A", opener=True), attack]}))
        first = behaviour.decide(Situation(state="Attack", dx=50, now=10.0, target_seen=10.0))
        used = {first.attack.name: 10.0}
        second = behaviour.decide(Situation(state="Attack", dx=50, now=11.0, attack_last_used=used, target_seen=11.0))
        self.assertEqual((first.attack.name, second.attack.name), ("Opener", "Attack 2"))

    def test_mobbing_counts_mobs_within_its_hit_range(self):
        attack = {"key": "Ctrl", "range_x": [10, 100], "range_y": [-30, 25]}
        p = profiles.from_dict("test", {"attacks": [dict(attack, key="Shift", name="Mobbing", min_mobs=2, hit_range=160), attack]})
        self.assertEqual(p.attack_for(50, 0, mobs=[(50, 0), (150, 0)]).name, "Mobbing")  # The second mob is past range_x, inside hit_range
        self.assertEqual(p.attack_for(50, 0, mobs=[(50, 0), (180, 0)]).name, "Attack 2")
        self.assertEqual((p.clump_range, profiles.load("swordsman").clump_range), (160, 100))

    def test_mobbing_counts_mobs_right_up_against_the_character(self):  # range_x's minimum is for picking targets, not for who gets hit
        self.assertEqual(self.attack(10.0, crowd=[(50, 0), (0, 0)]), "Mobbing attack")

    def test_mobbing_attack_needs_two_mobs_on_the_side_it_hits(self):
        self.assertEqual(self.attack(10.0, crowd=[(50, 0), (90, 5)]), "Mobbing attack")
        self.assertEqual(self.attack(10.0 + self.step, crowd=[(50, 0), (-60, 0)]), "Basic attack")  # The other mob is behind the player
        self.assertEqual(self.attack(10.0 + 2 * self.step, crowd=[(50, 0), (300, 0)]), "Basic attack")  # The other mob is out of reach

    def test_no_dash(self):
        self.assertEqual(decide("swordsman", state="Attack", dx=500).kind, "move")

    def test_needs_a_plain_attack(self):
        attack = {"key": "Ctrl", "range_x": [0, 100], "range_y": [-10, 10]}
        with self.assertRaises(profiles.ProfileError):
            profiles.from_dict("test", {"attacks": [dict(attack, opener=True), dict(attack, min_mobs=2)]})


class RangedTests(unittest.TestCase):
    def test_backs_off_when_mob_close(self):
        a = decide("hunter", state="Attack", dx=100, dy=0)
        self.assertEqual((a.kind, a.direction, a.label), ("move", "left", "back off"))

    def test_ignores_close_mob_on_another_platform(self):
        self.assertEqual(decide("hunter", state="Attack", dx=100, dy=150).kind, "stop")

    def test_shoots_in_range(self):
        a = decide("hunter", state="Attack", dx=-250, dy=10)
        self.assertEqual((a.kind, a.direction, a.attack.name), ("attack", "left", "Arrow Bomb"))

    def test_never_jump_attacks(self):
        self.assertEqual(decide("hunter", state="Attack", dx=250, dy=60).kind, "stop")

    def test_walks_without_mobility(self):
        self.assertEqual(decide("hunter", state="Attack", dx=600).kind, "move")

    def test_flash_jump_closes_distance(self):
        a = decide("assassin", state="Attack", dx=-300)
        self.assertEqual((a.kind, a.mobility.type, a.direction), ("mobility", "flash_jump", "left"))


class SharedTests(unittest.TestCase):
    def test_navigation(self):
        self.assertEqual(decide("spearman", state="Navigate", dx=400).kind, "mobility")
        self.assertEqual(decide("spearman", state="Navigate", dx=-100).kind, "move")
        a = decide("spearman", state="Navigate", dx=0, dy=50, on_ladder=True)
        self.assertEqual((a.kind, a.up), ("jump", True))
        self.assertEqual(decide("spearman", state="Navigate", dx=30, dy=50).kind, "move_jump")
        self.assertEqual(decide("spearman", state="Navigate", dx=30, dy=150).kind, "wait")

    def test_navigation_same_for_every_style(self):
        for dx, dy in [(-100, 0), (0, 50), (30, 50), (30, 150)]:
            self.assertEqual(decide("spearman", state="Navigate", dx=dx, dy=dy).kind, decide("hunter", state="Navigate", dx=dx, dy=dy).kind)

    def test_jiggles_to_find_a_covered_player(self):  # With Random Behaviour on: a little back and forth, after a moment
        b = behaviours.for_profile(profiles.load("swordsman"))
        lost = lambda now, randomizer=True: b.decide(Situation(state="Search", randomizer=randomizer, now=now))
        self.assertEqual(lost(10.0).label, "player not found")  # Waits first: usually it's covered for a moment
        first = lost(10.0 + behaviours.jiggle_after + 0.1)
        self.assertEqual((first.kind, first.label), ("move", "player not found: jiggling"))
        later = [lost(10.0 + behaviours.jiggle_after + 0.1 + i * 0.05) for i in range(1, 20)]
        self.assertIn("left", [a.direction for a in later if a.kind == "move"])
        self.assertIn("right", [a.direction for a in later if a.kind == "move"])  # Both ways, settling in between
        b2 = behaviours.for_profile(profiles.load("swordsman"))
        self.assertEqual(b2.decide(Situation(state="Search", now=20.0)).kind, "stop")
        self.assertEqual(b2.decide(Situation(state="Search", now=25.0)).kind, "stop")  # Random Behaviour off: only waits

    def test_search_and_idle(self):
        a = decide("hunter", state="Search", randomizer=True)
        self.assertEqual((a.kind, a.label), ("stop", "player not found"))  # Waits: it used to hold Up, grabbing any rope nearby
        self.assertEqual(decide("hunter").kind, "wait")


class ExecutorTests(unittest.TestCase):
    def run_action(self, profile_name, action):
        presses = []
        e = executor.Executor(profiles.load(profile_name))
        with mock.patch.object(keyboard, "PressKey", lambda k: presses.append(k)), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: None), mock.patch("time.sleep"):
            e.run(action)
        return e, presses

    def test_attack_uses_profile_key_and_records_use(self):
        p = profiles.load("hunter")
        e, presses = self.run_action("hunter", behaviours.Action("attack", "right", attack=p.attacks[0]))
        self.assertEqual(presses, [keyboard.VK_RIGHT, keyboard.VK_SHIFT])  # Face right, then Arrow Bomb on Shift
        self.assertIn("Arrow Bomb", e.attack_last_used)

    def test_turns_only_when_facing_changes(self):  # Each arrow tap also walks a step
        p = profiles.load("swordsman")
        e, presses = self.run_action("swordsman", behaviours.Action("attack", "right", attack=p.attacks[-1]))
        with mock.patch.object(keyboard, "PressKey", lambda k: presses.append(k)),                 mock.patch.object(keyboard, "ReleaseKey", lambda k: None), mock.patch("time.sleep"):
            e.run(behaviours.Action("attack", "right", attack=p.attacks[-1]))
            e.run(behaviours.Action("attack", "left", attack=p.attacks[-1]))
        self.assertEqual(presses, [keyboard.VK_RIGHT, keyboard.VK_CONTROL, keyboard.VK_CONTROL, keyboard.VK_LEFT, keyboard.VK_CONTROL])

    def test_loot_key_rate_limited(self):  # Pressed every bot tick it reached ~75 a second and froze the game client
        e = executor.Executor(profiles.load("swordsman"))
        presses = []
        clock = [100.0]
        with mock.patch.object(keyboard, "PressKey", lambda k: presses.append(k)), mock.patch.object(keyboard, "ReleaseKey", lambda k: None),                 mock.patch("time.sleep"), mock.patch("time.time", lambda: clock[0]):
            for _ in range(100):  # One second of ticks, 10 ms apart
                e.loot()
                clock[0] += 0.01
        self.assertEqual(presses.count(keyboard.VK_Z), 10)

    def test_taps_are_timed_like_a_person(self):  # With Human Key Presses on
        from data import config
        e = executor.Executor(profiles.load("swordsman"))
        sleeps, clock = [], [100.0]

        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds

        with mock.patch.object(keyboard, "PressKey"), mock.patch.object(keyboard, "ReleaseKey"), mock.patch.object(values, "human_input", True), \
                mock.patch("time.sleep", sleep), mock.patch("time.time", lambda: clock[0]):
            first = e.press(keyboard.VK_CONTROL)
            second = e.press(keyboard.VK_CONTROL)
        holds = [sleeps[0], sleeps[-1]]
        self.assertTrue(all(config.press_time[0] <= h <= config.press_time[1] for h in holds))
        self.assertGreaterEqual(second - first, config.press_time[0] + config.press_gap[0])  # Not mashed faster than a person could

    def test_exact_presses_when_human_timing_is_off(self):  # The default: instant and fixed, for responsiveness
        e = executor.Executor(profiles.load("swordsman"))
        sleeps = []
        with mock.patch.object(keyboard, "PressKey"), mock.patch.object(keyboard, "ReleaseKey"), mock.patch.object(values, "human_input", False), \
                mock.patch("time.sleep", sleeps.append):
            e.press(keyboard.VK_CONTROL)
            e.press(keyboard.VK_CONTROL)
            e.pause(0.25)
        self.assertEqual(sleeps, [0.01, 0.01, 0.25])

    def test_overlapping_mob_is_attacked_without_turning(self):  # Its side jitters by a few pixels; turning each time walks a step
        a = decide("swordsman", state="Attack", dx=0, dy=0, now=10.0, target_seen=9.98, facing="left")
        self.assertEqual((a.kind, a.direction), ("attack", None))
        e, presses = self.run_action("swordsman", a)
        self.assertNotIn(keyboard.VK_LEFT, presses)
        self.assertNotIn(keyboard.VK_RIGHT, presses)

    def test_overlapping_target_counts_mobs_the_way_it_faces(self):
        s = Situation(state="Attack", dx=0, crowd=[(0, 0), (60, 0), (-60, 0), (-80, 0)], facing="left")
        self.assertEqual(len(s.mobs_ahead()), 3)  # The overlapping one and the two on the left

    def test_rope_actions(self):
        self.assertEqual(decide("swordsman", state="Navigate", route="climb", on_ladder=True).kind, "climb")
        far = decide("swordsman", state="Navigate", route="up", dx=100, dy=40, on_ladder=True)
        self.assertEqual((far.kind, far.label), ("move", "move to the rope"))  # Ropes are caught jumping straight up under them
        running = decide("swordsman", state="Navigate", route="up", dx=-40, dy=40, on_ladder=True)
        self.assertEqual((running.kind, running.direction, running.up), ("move_jump", "left", True))  # Grabbed in the air, moving
        near = decide("swordsman", state="Navigate", route="up", dx=-10, dy=40, on_ladder=True)
        self.assertEqual((near.kind, near.direction), ("nudge", "left"))  # Right by it: taps, then a straight jump
        off = decide("swordsman", state="Navigate", route="jump_off", dx=-1, on_ladder=True)
        self.assertEqual((off.kind, off.direction), ("jump_off", "left"))
        under = decide("swordsman", state="Navigate", route="up", dx=0, dy=40, on_ladder=True)
        self.assertEqual((under.kind, under.up), ("jump", True))

    def test_up_held_through_jump_and_climb_then_let_go(self):
        e = executor.Executor(profiles.load("swordsman"))
        events = []
        with mock.patch.object(keyboard, "PressKey", lambda k: events.append(("down", k))), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: events.append(("up", k))), mock.patch("time.sleep"):
            e.run(behaviours.Action("jump", up=True))
            e.run(behaviours.Action("climb"))
            self.assertNotIn(("up", keyboard.VK_UP), events)  # Still held, onto the rope and up it
            e.run(behaviours.Action("stop"))
        self.assertEqual(events[-1], ("up", keyboard.VK_UP))
        self.assertFalse(e.holding_up)

    def test_no_quick_turning_back(self):  # Jitter in the target's side used to flip the character left and right
        b = behaviours.for_profile(profiles.load("swordsman"))
        walk = lambda now, dx: b.decide(Situation(state="Attack", dx=dx, dy=0, now=now, target_seen=now))
        self.assertEqual(walk(10.0, 300).kind, "move")
        settle = walk(10.1, -300)
        self.assertEqual((settle.kind, settle.label), ("stop", "settling before turning back"))
        self.assertEqual((walk(10.5, -300).kind, walk(10.6, -300).direction), ("move", "left"))  # Turned once it had settled

    def test_holds_on_after_jumping_at_a_rope(self):  # Jumping again straight away would leave the rope it just caught
        b = behaviours.for_profile(profiles.load("swordsman"))
        rope = lambda now, dx=0: b.decide(Situation(state="Navigate", route="up", dx=dx, dy=40, on_ladder=True, now=now))
        self.assertEqual(rope(10.0).label, "jump onto the rope")
        self.assertEqual((rope(10.3).kind, rope(10.4, dx=15).kind), ("climb", "climb"))  # Even if it drifted a little
        self.assertEqual(rope(11.0).label, "jump onto the rope")  # Long enough to know it missed: try again

    def walk(self, randomizer=True, speed=-125.0, dx=-1000, state="Navigate", seconds=0.6):  # Walking ticks; the last action
        b = behaviours.for_profile(profiles.load("swordsman"))
        actions = [b.decide(Situation(state=state, route="walk", dx=dx, dy=0, randomizer=randomizer, speed=speed, now=10 + i * 0.05,
                                      target_seen=10 + i * 0.05)) for i in range(int(seconds / 0.05) + 1)]
        return actions[0], actions[-1]

    def test_hops_along_long_walks_once_up_to_speed(self):  # Jumping from a standstill only goes straight up
        first, later = self.walk()
        self.assertFalse(first.jump)
        self.assertEqual((later.kind, later.direction, later.jump, later.label), ("move", "left", True, "move towards mob (jumping)"))
        self.assertFalse(self.walk(speed=-30.0)[1].jump)  # Not really moving (pushing against something): no hopping
        self.assertTrue(self.walk(speed=None)[1].jump)  # Speed unknown: walking long enough will do
        self.assertFalse(self.walk(randomizer=False)[1].jump)  # Random Behaviour off: walks
        self.assertFalse(self.walk(dx=-300)[1].jump)  # Within jump_move_distance: walks
        self.assertTrue(self.walk(state="Attack", dx=-900)[1].jump)  # A far mob, too

    def test_keeps_holding_jump_while_hopping(self):  # Letting go on a speed dip (mid-air, landing) left pauses between hops
        b = behaviours.for_profile(profiles.load("swordsman"))
        tick = lambda now, speed: b.decide(Situation(state="Navigate", route="walk", dx=-1000, randomizer=True, speed=speed, now=now))
        jumps = [tick(10 + i * 0.05, -125.0).jump for i in range(12)]
        self.assertTrue(jumps[-1])
        self.assertTrue(tick(10.6, -20.0).jump)  # Speed dipped: still held

    def test_jump_held_while_hopping_then_let_go(self):
        e = executor.Executor(profiles.load("swordsman"))
        events = []
        with mock.patch.object(keyboard, "PressKey", lambda k: events.append(("down", k))),                 mock.patch.object(keyboard, "ReleaseKey", lambda k: events.append(("up", k))), mock.patch("time.sleep"):
            e.run(behaviours.Action("move", "right", jump=True))
            self.assertTrue(e.holding_jump)
            e.run(behaviours.Action("move", "right"))
        self.assertIn(("up", keyboard.VK_MENU), events)
        self.assertFalse(e.holding_jump)

    def test_nudge_and_jump_off_keys(self):
        e, presses = self.run_action("swordsman", behaviours.Action("nudge", "right"))
        self.assertEqual(presses, [keyboard.VK_RIGHT])
        e, presses = self.run_action("swordsman", behaviours.Action("jump_off", "left"))
        self.assertEqual(presses, [keyboard.VK_LEFT, keyboard.VK_MENU])  # Direction held, then jump: off the rope sideways
        self.assertEqual(e.facing, keyboard.VK_LEFT)

    def test_flash_jump_presses_jump_twice(self):
        p = profiles.load("assassin")
        e, presses = self.run_action("assassin", behaviours.Action("mobility", "left", mobility=p.mobility[0]))
        self.assertEqual(presses.count(keyboard.VK_MENU), 2)

    def test_stop_moving_releases_held_arrow(self):
        e = executor.Executor(profiles.load("spearman"))
        released = []
        with mock.patch.object(keyboard, "PressKey", lambda k: None), \
                mock.patch.object(keyboard, "ReleaseKey", lambda k: released.append(k)), mock.patch("time.sleep"):
            e.move(keyboard.VK_LEFT)
            e.stop_moving()
        self.assertEqual((released, e.held_direction), ([keyboard.VK_LEFT], None))


if __name__ == "__main__":
    unittest.main()
