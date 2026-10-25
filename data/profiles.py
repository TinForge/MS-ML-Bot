# Bot profiles: what a character build can do, loaded from profiles/<name>.toml

import os
import tomllib
from dataclasses import dataclass, field

folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "profiles")

BEHAVIOURS = ("melee", "ranged")  # Implemented in process/behaviours.py
MOBILITY_TYPES = ("dash", "flash_jump", "teleport")


class ProfileError(Exception):
    pass


@dataclass
class Attack:
    name: str
    key: str
    range_x: tuple  # (min, max) horizontal distance to the mob
    range_y: tuple  # (min, max) height of the mob above the player
    jump_attack: bool = False  # Can be used mid-jump against mobs just above range_y
    jump_reach: int = 75  # How much higher a jump attack reaches than range_y
    cooldown: float = 0  # Seconds before it can be used again

    def reaches(self, distance, height):
        return self.range_x[0] <= distance <= self.range_x[1] and self.range_y[0] <= height <= self.range_y[1]

    def reaches_jumping(self, distance, height):
        return self.jump_attack and self.range_x[0] <= distance <= self.range_x[1] and self.range_y[1] < height <= self.range_y[1] + self.jump_reach


@dataclass
class Mobility:
    type: str  # dash, flash_jump or teleport
    min_distance: int  # Used when the target is farther away than this
    key: str = None  # Not needed for flash_jump, which uses the jump key


@dataclass
class Profile:
    name: str
    behaviour: str
    attacks: list
    keys: dict = field(default_factory=lambda: {"jump": "Alt", "loot": "Z"})
    mobility: list = field(default_factory=list)
    platform_range: int = 50  # Distance to a platform or ladder within which the bot jumps for it
    platform_height: int = 100  # Highest platform the bot tries to jump onto
    keep_distance: int = 0  # Ranged: back off from mobs closer than this
    description: str = ""

    def attack_for(self, distance, height, last_used=None, now=0):  # First ready attack that reaches the target, or None
        for attack in self.ready_attacks(last_used, now):
            if attack.reaches(distance, height):
                return attack
        return None

    def jump_attack_for(self, distance, height, last_used=None, now=0):
        for attack in self.ready_attacks(last_used, now):
            if attack.reaches_jumping(distance, height):
                return attack
        return None

    def ready_attacks(self, last_used, now):
        last_used = last_used or {}
        return [a for a in self.attacks if now - last_used.get(a.name, -1e9) >= a.cooldown]

    def mobility_for(self, distance):  # The longest-range mobility the distance calls for, or None
        usable = [m for m in self.mobility if distance > m.min_distance]
        return max(usable, key=lambda m: m.min_distance) if usable else None

    @property
    def max_range(self):
        return max(a.range_x[1] for a in self.attacks)

    @property
    def min_range(self):
        return min(a.range_x[0] for a in self.attacks)


def available():  # Profile names from the profiles folder
    if not os.path.isdir(folder):
        return []
    return sorted(f[:-5] for f in os.listdir(folder) if f.endswith(".toml"))


def load(name):  # Raises ProfileError with a readable message if the file is missing or invalid
    path = os.path.join(folder, name + ".toml")
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except FileNotFoundError:
        raise ProfileError("profile '%s' not found in profiles/" % name)
    except tomllib.TOMLDecodeError as e:
        raise ProfileError("%s.toml could not be read: %s" % (name, e))
    return from_dict(name, data)


def from_dict(name, data):
    from tools import keyboard  # Key names are checked here so a typo is reported when the profile loads

    def key_name(value, where):
        if value not in keyboard.BIND_NAMES:
            raise ProfileError("%s: %s key '%s' is not a known key (e.g. Ctrl, Alt, Shift, Space, A-Z, 0-9, Insert, Page Up)" % (name, where, value))
        return value

    def pair(value, where):
        if not isinstance(value, list) or len(value) != 2 or not all(isinstance(v, (int, float)) for v in value) or value[0] > value[1]:
            raise ProfileError("%s: %s must be [min, max]" % (name, where))
        return tuple(value)

    behaviour = data.get("behaviour", "melee")
    if behaviour not in BEHAVIOURS:
        raise ProfileError("%s: behaviour must be one of %s" % (name, ", ".join(BEHAVIOURS)))

    keys = {"jump": "Alt", "loot": "Z"}
    for k, v in data.get("keys", {}).items():
        keys[k] = key_name(v, k)

    attacks = []
    for i, a in enumerate(data.get("attacks", [])):
        where = "attack '%s'" % a.get("name", i + 1)
        if "key" not in a or "range_x" not in a or "range_y" not in a:
            raise ProfileError("%s: %s needs key, range_x and range_y" % (name, where))
        attacks.append(Attack(name=a.get("name", "Attack %d" % (i + 1)), key=key_name(a["key"], where),
                              range_x=pair(a["range_x"], where + " range_x"), range_y=pair(a["range_y"], where + " range_y"),
                              jump_attack=bool(a.get("jump_attack", False)), jump_reach=a.get("jump_reach", 75), cooldown=a.get("cooldown", 0)))
    if not attacks:
        raise ProfileError("%s: needs at least one [[attacks]] entry" % name)

    mobility = []
    for m in data.get("mobility", []):
        if m.get("type") not in MOBILITY_TYPES:
            raise ProfileError("%s: mobility type must be one of %s" % (name, ", ".join(MOBILITY_TYPES)))
        if m["type"] != "flash_jump" and "key" not in m:
            raise ProfileError("%s: %s mobility needs a key" % (name, m["type"]))
        mobility.append(Mobility(type=m["type"], min_distance=m.get("min_distance", 350), key=key_name(m["key"], m["type"]) if "key" in m else None))

    movement = data.get("movement", {})
    return Profile(name=name, behaviour=behaviour, attacks=attacks, keys=keys, mobility=mobility,
                   platform_range=movement.get("platform_range", 50), platform_height=movement.get("platform_height", 100),
                   keep_distance=data.get("ranged", {}).get("keep_distance", 0), description=data.get("description", ""))
