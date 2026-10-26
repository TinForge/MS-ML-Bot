# Fighting styles: decide what to do from a snapshot of the game, without pressing any keys

from dataclasses import dataclass, field

from data import values
from data.profiles import Profile


@dataclass
class Situation:  # One tick's view of the game, built from values set by calculations.py
    state: str = None  # Attack, Navigate, Search, or None when there's nothing to do
    dx: float = 0  # Horizontal distance to the target: negative is left
    dy: float = 0  # How far the target is above the player
    on_ladder: bool = False  # Navigate target is a ladder
    route: str = None  # Navigate: up, down or walk (see process/navigation.py)
    randomizer: bool = False  # Random Behaviour is on
    now: float = 0
    attack_last_used: dict = field(default_factory=dict)  # Attack name: time it was last used
    target_seen: float = None  # Attack: time.time() of the detection frame the mob was last seen in, None if unknown
    crowd: list = None  # Attack: (dx, dy) of every mob in reach, the target included
    target_health: float = None  # Attack: share of the target's health left from its bar this frame, None if no bar is showing
    facing: str = None  # Which way the character faces, left or right, None if unknown

    def mobs_ahead(self):  # (distance, height) of the mobs on the target's side or overlapping the player, which an attack facing it can hit
        crowd = self.crowd if self.crowd else [(self.dx, self.dy)]
        side = self.dx or {"left": -1, "right": 1}.get(self.facing, 0)  # Target overlapping: the way the character faces (unknown: both)
        return [(abs(dx), dy) for dx, dy in crowd if dx * side >= 0]

    def mobs_in_reach(self, attack):  # How many mobs an attack aimed at the target would hit
        return sum(attack.hits(d, h) for d, h in self.mobs_ahead())

    @property
    def last_attack(self):  # When any attack was last used
        return max(self.attack_last_used.values(), default=-1e9)

    @property
    def last_attack_name(self):  # Which attack was used last, None before the first
        return max(self.attack_last_used, key=self.attack_last_used.get) if self.attack_last_used else None

    @property
    def direction(self):
        return "left" if self.dx < 0 else "right"

    @property
    def away(self):
        return "right" if self.dx < 0 else "left"

    @classmethod
    def from_values(cls, now, attack_last_used, facing=None):
        state = values.debug_state
        if state == "Attack" and values.debug_mob is None or state == "Navigate" and values.debug_path is None:
            state = None  # The state is left over from an earlier tick
        mob = values.debug_mob
        seen = mob.timestamp / 1000 if state == "Attack" and mob is not None and mob.timestamp else None  # Rect timestamps are in ms
        return cls(state=state, dx=values.debug_x_distance, dy=values.debug_y_distance, on_ladder=values.debug_on_ladder, route=values.debug_route,
                   randomizer=values.randomizer_active, now=now, attack_last_used=attack_last_used, target_seen=seen,
                   crowd=list(values.debug_crowd or []) if state == "Attack" else None,
                   target_health=mob.health if state == "Attack" and mob is not None else None, facing=facing)


@dataclass
class Action:  # What the executor should do this tick
    kind: str  # attack, jump_attack, move, mobility, stop, jump, move_jump, drop, climb, wait
    direction: str = None  # left or right
    attack: object = None
    mobility: object = None
    up: bool = False  # Hold Up while jumping, to grab a ladder
    random_jump: bool = False
    label: str = ""  # Shown in the Diagnostics panel


new_target_gap = 1.5  # Seconds without attacking after which the next target counts as a new mob
new_target_shift = 60  # How far the target may move between attacks (knockback, walking) and still be the same mob


class Behaviour:  # Shared by every style: navigating between platforms and searching for the player
    def __init__(self, profile: Profile):
        self.profile = profile
        self.last_target = None  # (time, dx, dy) of the last attack, to tell a new mob from the one being fought
        self.seen_health = None  # Health last read from the bar of the mob being fought; kept while the bar is hidden for a frame

    def same_target(self, s: Situation):  # Whether the target is the mob attacked last
        if self.last_target is None:
            return False
        when, dx, dy = self.last_target
        return s.now - when <= new_target_gap and abs(s.dx - dx) <= new_target_shift and abs(s.dy - dy) <= new_target_shift

    def track_health(self, s: Situation):  # Remembers the target's health from its bar, for picking attacks while the bar is hidden
        if not self.same_target(s):
            self.seen_health = None
        if s.target_health is not None:
            self.seen_health = s.target_health

    def new_target(self, s: Situation):  # Whether the target hasn't been hit yet, so an opener attack applies
        return self.seen_health is None and not self.same_target(s)

    def pick_attack(self, s: Situation, jumping=False):
        p = self.profile
        find = p.jump_attack_for if jumping else p.attack_for
        return find(abs(s.dx), s.dy, s.attack_last_used, s.now, new_target=self.new_target(s), mobs=s.mobs_ahead(), health=self.seen_health)

    def decide(self, s: Situation) -> Action:
        if s.state == "Attack":
            self.track_health(s)
            return self.fight(s)
        if s.state == "Navigate":
            return self.navigate(s)
        if s.state == "Search":  # The nametag is usually just covered for a moment: wait (pressing Up here used to grab ropes)
            return Action("stop", label="player not found")
        return Action("wait", label="nothing")

    def fight(self, s: Situation) -> Action:
        raise NotImplementedError

    def strike(self, s: Situation, kind, attack, label):  # Judges the target on frames grabbed after the last hit landed. A bar shows it's
        # alive: attack again right away. No bar: watch gone_delay longer, and attack only if it's still there (a dead mob fades out)
        last = self.profile.attack_named(s.last_attack_name) if s.last_attack_name else None
        if last is not None:
            landed = s.last_attack + last.hit_time
            seen = s.target_seen if s.target_seen is not None else s.now
            if seen < landed:  # Stop, not wait, while holding off: wait would leave a held arrow key walking into the mob
                return Action("stop", label="waiting for the hit to land")
            if s.target_health is None and seen < landed + self.profile.gone_delay:
                return Action("stop", label="no bar: checking the mob is gone")
        self.last_target = (s.now, s.dx, s.dy)
        direction = s.direction if s.dx != 0 else None  # Overlapping the character: keep facing as is, or it turns back and forth over it
        mobbing = [a for a in self.profile.attacks if a.min_mobs > 1]
        counted = " (%d in mobbing reach)" % s.mobs_in_reach(mobbing[0]) if mobbing else ""  # For tuning hit_range in Diagnostics
        return Action(kind, direction, attack=attack, label=label + attack.name + counted)

    def approach(self, s: Situation, random_jump=False):  # Fastest way to close the distance
        mobility = self.profile.mobility_for(abs(s.dx))
        if mobility is not None:
            return Action("mobility", s.direction, mobility=mobility, random_jump=random_jump, label="move closer (%s)" % mobility.type.replace("_", " "))
        return Action("move", s.direction, random_jump=random_jump, label="move closer")

    def navigate(self, s: Situation) -> Action:
        p = self.profile
        distance = abs(s.dx)
        if s.route == "climb":  # On a rope: hold Up until off at the top
            return Action("climb", label="climbing")
        if p.mobility_for(distance) is not None:
            return self.approach(s)
        if s.route == "down":  # Get over the lower platform, then drop through
            if distance > 0:
                return Action("move", s.direction, label="move to drop")
            return Action("drop", label="drop down")
        if s.route == "walk":  # Head for a mob on another platform without jumping
            return Action("move", s.direction, label="move towards mob")
        if distance > p.platform_range or (s.on_ladder and distance > 0):  # A rope is only caught by jumping straight up under it
            return Action("move", s.direction, label="move to the rope" if s.on_ladder else "move closer")
        if distance == 0 and s.dy < p.platform_height:
            return Action("jump", up=s.on_ladder, label="jump onto the rope" if s.on_ladder else "jump")
        if distance < p.platform_range and s.dy < p.platform_height:
            return Action("move_jump", s.direction, up=s.on_ladder, label="moving jump")
        return Action("wait", label="platform out of reach")


class MeleeBehaviour(Behaviour):  # Close in, attack, jump attack mobs slightly above
    def fight(self, s: Situation) -> Action:
        p = self.profile
        distance, height = abs(s.dx), s.dy
        if p.mobility_for(distance) is not None:
            return self.approach(s, random_jump=s.randomizer)
        attack = self.pick_attack(s)
        if attack is not None:
            return self.strike(s, "attack", attack, "attack: ")
        attack = self.pick_attack(s, jumping=True)
        if attack is not None:
            return self.strike(s, "jump_attack", attack, "jump attack: ")
        if distance > p.max_range:
            return Action("move", s.direction, label="move closer")
        if distance < p.min_range:
            return Action("move", s.away, label="move away")
        return Action("stop", label="mob out of reach")


class RangedBehaviour(Behaviour):  # Keep distance, shoot from range, never jump attack
    def fight(self, s: Situation) -> Action:
        p = self.profile
        distance, height = abs(s.dx), s.dy
        if p.mobility_for(distance) is not None:
            return self.approach(s, random_jump=s.randomizer)
        same_level = any(a.range_y[0] <= height <= a.range_y[1] for a in p.attacks)  # Mobs on other platforms aren't a threat
        if distance < p.keep_distance and same_level:
            return Action("move", s.away, label="back off")
        attack = self.pick_attack(s)
        if attack is not None:
            return self.strike(s, "attack", attack, "attack: ")
        if distance > p.max_range:
            return Action("move", s.direction, label="move closer")
        if distance < p.min_range and same_level:
            return Action("move", s.away, label="move away")
        return Action("stop", label="mob out of reach")


BEHAVIOURS = {"melee": MeleeBehaviour, "ranged": RangedBehaviour}  # Profile behaviour name: class


def for_profile(profile: Profile) -> Behaviour:
    return BEHAVIOURS[profile.behaviour](profile)
