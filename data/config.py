# Tunable values, loaded once from config.toml at the repository root

import os
import tomllib

path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.toml")

# Used for anything missing from config.toml or of the wrong type
DEFAULTS = {
    "detection": {"stats_interval": 0.25, "player_interval": 0.05, "model": "yolo11", "model_imgsz": 960},
    "player": {"search_margin": (120, 80), "character_size": (50, 66), "nametag_tolerance": 0.05},
    "potion": {"cooldown": 3.0, "confirm_reads": 2},
    "display": {"window_width": 390, "drop_display_time": 1.5, "potion_display_time": 1.5},
    "frame_times": {"smoothing": 0.1, "stale_time": 1.0},
    "input": {"press_time": (0.07, 0.12), "press_gap": (0.05, 0.12), "hold_jitter": 0.1},
    "movement": {"explore_delay": 3.0},
}


MODELS = ("yolo11", "yolov5")  # Detection models: folders with a model.py and weights.pt


def convert(value, default):  # Returns value in the default's type, or raises ValueError
    if isinstance(default, str):
        if not isinstance(value, str):
            raise ValueError("expected text in quotes")
        if default in MODELS and value not in MODELS:
            raise ValueError("expected one of %s" % ", ".join(MODELS))
        return value
    if isinstance(default, tuple):
        if not isinstance(value, list) or len(value) != len(default):
            raise ValueError("expected a list of %d numbers" % len(default))
        return tuple(convert(v, d) for v, d in zip(value, default))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected a number")
    if isinstance(default, int) and value != int(value):
        raise ValueError("expected a whole number")
    return type(default)(value)


def load():
    settings = {section: dict(keys) for section, keys in DEFAULTS.items()}
    try:
        with open(path, "rb") as f:
            loaded = tomllib.load(f)
    except FileNotFoundError:
        return settings
    except tomllib.TOMLDecodeError as e:
        print("config.toml could not be read, using defaults:", e)
        return settings
    for section, keys in DEFAULTS.items():
        for key, default in keys.items():
            if key in loaded.get(section, {}):
                try:
                    settings[section][key] = convert(loaded[section][key], default)
                except ValueError as e:
                    print("config.toml [%s] %s: %s, using %r" % (section, key, e, default))
    return settings


settings = load()

stats_interval = settings["detection"]["stats_interval"]
player_interval = settings["detection"]["player_interval"]
detection_model = settings["detection"]["model"]
model_imgsz = settings["detection"]["model_imgsz"]
search_margin = settings["player"]["search_margin"]
character_size = settings["player"]["character_size"]
nametag_tolerance = settings["player"]["nametag_tolerance"]
potion_cooldown = settings["potion"]["cooldown"]
potion_confirm_reads = settings["potion"]["confirm_reads"]
window_width = settings["display"]["window_width"]
drop_display_time = settings["display"]["drop_display_time"]
potion_display_time = settings["display"]["potion_display_time"]
timing_smoothing = settings["frame_times"]["smoothing"]
timing_stale_time = settings["frame_times"]["stale_time"]
press_time = settings["input"]["press_time"]
press_gap = settings["input"]["press_gap"]
hold_jitter = settings["input"]["hold_jitter"]
explore_delay = settings["movement"]["explore_delay"]
