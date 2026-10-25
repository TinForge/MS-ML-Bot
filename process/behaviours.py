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

    @property
    def direction(self):
        return "left" if self.dx < 0 else "right"

    @property
    def away(self):
        return "right" if self.dx < 0 else "left"

    @classmethod
    def from_values(cls, now, attack_last_used):
        state = values.debug_state
        if state == "Attack" and values.debug_mob is None or state == "Navigate" and values.debug_path is None:
            state = None  # The state is left over from an earlier tick
        return cls(state=state, dx=values.debug_x_distance, dy=values.debug_y_distance, on_ladder=values.debug_on_ladder, route=values.debug_route,
                   randomizer=values.randomizer_active, now=now, attack_last_used=attack_last_used)


@dataclass
class Action:  # What the executor should do this tick
    kind: str  # attack, jump_attack, move, mobility, stop, jump, move_jump, drop, search, wait
    direction: str = None  # left or right
    attack: object = None
    mobility: object = None
    up: bool = False  # Hold Up while jumping, to grab a ladder
    random_jump: bool = False
    random_move: bool = False
    label: str = ""  # Shown in the Diagnostics panel


class Behaviour:  # Shared by every style: navigating between platforms and searching for the player
    def __init__(self, profile: Profile):
        self.profile = profile

    def decide(self, s: Situation) -> Action:
        if s.state == "Attack":
            return self.fight(s)
        if s.state == "Navigate":
            return self.navigate(s)
        if s.state == "Search":
            return Action("search", random_move=s.randomizer, label="search")
        return Action("wait", label="nothing")

    def fight(self, s: Situation) -> Action:
        raise NotImplementedError

    def approach(self, s: Situation, random_jump=False):  # Fastest way to close the distance
        mobility = self.profile.mobility_for(abs(s.dx))
        if mobility is not None:
            return Action("mobility", s.direction, mobility=mobility, random_jump=random_jump, label="move closer (%s)" % mobility.type.replace("_", " "))
        return Action("move", s.direction, random_jump=random_jump, label="move closer")

    def navigate(self, s: Situation) -> Action:
        p = self.profile
        distance = abs(s.dx)
        if p.mobility_for(distance) is not None:
            return self.approach(s)
        if s.route == "down":  # Get over the lower platform, then drop through
            if distance > 0:
                return Action("move", s.direction, label="move to drop")
            return Action("drop", label="drop down")
        if s.route == "walk":  # Head for a mob on another platform without jumping
            return Action("move", s.direction, label="move towards mob")
        if distance > p.platform_range:
            return Action("move", s.direction, label="move closer")
        if distance == 0 and s.dy < p.platform_height:
            return Action("jump", up=s.on_ladder, label="jump")
        if distance < p.platform_range and s.dy < p.platform_height:
            return Action("move_jump", s.direction, up=s.on_ladder, label="moving jump")
        return Action("wait", label="platform out of reach")


class MeleeBehaviour(Behaviour):  # Close in, attack, jump attack mobs slightly above
    def fight(self, s: Situation) -> Action:
        p = self.profile
        distance, height = abs(s.dx), s.dy
        if p.mobility_for(distance) is not None:
            return self.approach(s, random_jump=s.randomizer)
        attack = p.attack_for(distance, height, s.attack_last_used, s.now)
        if attack is not None:
            return Action("attack", s.direction, attack=attack, label="attack: " + attack.name)
        attack = p.jump_attack_for(distance, height, s.attack_last_used, s.now)
        if attack is not None:
            return Action("jump_attack", s.direction, attack=attack, label="jump attack: " + attack.name)
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
        attack = p.attack_for(distance, height, s.attack_last_used, s.now)
        if attack is not None:
            return Action("attack", s.direction, attack=attack, label="attack: " + attack.name)
        if distance > p.max_range:
            return Action("move", s.direction, label="move closer")
        if distance < p.min_range and same_level:
            return Action("move", s.away, label="move away")
        return Action("stop", label="mob out of reach")


BEHAVIOURS = {"melee": MeleeBehaviour, "ranged": RangedBehaviour}  # Profile behaviour name: class


def for_profile(profile: Profile) -> Behaviour:
    return BEHAVIOURS[profile.behaviour](profile)
