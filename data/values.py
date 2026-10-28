# Global values

from tools import window_functions
from tools import overlay

from process import calculations, detection, bot


window_found = False
window_active = False
window_rect = None  # Game client area in screen pixels (x1, y1, x2, y2), None if not found
show_window_rect = False

# Set by detection.py from the status bar, (current, max) or None if not readable
player_hp = None
player_mp = None
player_exp = None  # (exp, percent) from the status bar, None if unknown
stats_read_id = 0  # Increments with every HP/MP reading
player_read_id = 0  # Increments with every search for the player (and map reading), which calculations plan from
player_name = None  # Name pixels (bool array) from the status bar
player_rect = None  # Player character in screen pixels (x1, y1, x2, y2), found by their nametag
show_player_rect = False
minimap = None  # tools.minimap.Minimap with its map area in screen pixels, or None if not shown
show_minimap = False
record_platforms = False
show_platforms = False
show_attack_range = False  # Draws the bot profile's attack ranges around the player on the overlay
mapper = None  # tools.map_recorder.Mapper, set by detection.py

# Set through tools/timer.py, name: (smoothed ms, time.time() of last sample)
timings = {}

detection_active = False
model_loading = False  # Detection is on but its model is still loading (first use)
calculations_active = False
bot_active = False

looting_active = False
randomizer_active = False
human_input = False  # Human Key Presses: bot taps timed like a person's (config.toml [input]) instead of exact and instant
potion_active = False
exp_check_active = True  # EXP Kill Check: kills told from EXP going up (process/kills.py)

# Set by bot_panel.py; bot.py reloads the profile whenever the name or version changes
bot_profile = None
bot_profile_version = 0
bot_profile_error = None  # Message if the picked profile could not be loaded

# Set by stats_panel.py; a threshold of 0 turns that potion off
hp_potion_threshold = 0
mp_potion_threshold = 0
hp_potion_key = "Delete"
mp_potion_key = "End"

# Set by bot.py, time.time() of the last potion per stat
last_potion_time = {"HP": 0, "MP": 0}


overlay_visible = False

# Set by detection.py
detected_instances = None  
debug_player = None
debug_platform = None
debug_mob = None
debug_crowd = []  # (dx, dy) of each mob in the player's reach, set with debug_mob
debug_x_distance = 0
debug_y_distance = 0
debug_direction = None
debug_path = None
debug_on_ladder = False
debug_route = None  # Navigate: up, down or walk
nav_jump_height = 100  # Highest platform worth jumping for, from the bot profile
player_speed = None  # Sideways speed in px/s from the movement tracker (negative: left), None if unknown
planned_route = None  # Map points of the route being followed across the recorded map (see RoutePlanner.path), None without one
nav_clump_range = 0  # How far in front the profile's mobbing attack hits, 0 without one

debug_action = "nothing"
debug_state = "nothing"

model_iou = 0.5
model_conf = 0.9



def update():
    # Window
    global window_found
    window_found = window_functions.is_maple_found()
    global window_active
    window_active = window_functions.is_maple_active()
    global window_rect
    window_rect = window_functions.get_maple_client_rect()

    # Process
    global detection_active, model_loading
    if detection.instance:
        detection_active = detection.instance.is_running
        model_loading = detection.instance.is_running and detection.instance.model is None
    global calculations_active
    if calculations.instance:
        calculations_active = calculations.instance.is_running
    global bot_active
    if bot.instance:
        bot_active = bot.instance.is_running

    # Debug
    global overlay_visible
    overlay_visible = overlay.is_visible
