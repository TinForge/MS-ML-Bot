# Global values

from tools import window_functions
from tools import overlay

from process import calculations, detection, bot


window_found = False
window_active = False
window_rect = None

detection_active = False
calculations_active = False
bot_active = False

overlay_visible = False

# Set by detection.py
detected_instances = None  
debug_player = None
debug_mob = None
debug_x_distance = 0
debug_y_distance = 0
debug_direction = None
debug_action = "nothing"


def update():
    # Window
    global window_found
    window_found = window_functions.is_found()
    global window_active
    window_active = window_functions.is_active()
    global window_rect
    window_rect = window_functions.get_rect()

    # Process
    global detection_active
    if detection.instance:
        detection_active = detection.instance.is_running
    global calculations_active
    if calculations.instance:
        calculations_active = calculations.instance.is_running
    global bot_active
    if bot.instance:
        bot_active = bot.instance.is_running

    # Debug
    global overlay_visible
    overlay_visible = overlay.is_visible
