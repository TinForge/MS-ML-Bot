# Global values

from tools import window_functions
from tools import overlay

from process import decision, detection


window_found = False
window_active = False
window_rect = None

detection_active = False
decision_active = False

overlay_visible = False

detected_instances = None  # Set by detection.py
debug_player = None  # 
debug_monster = None  # 
debug_action = "Null"
debug_distance = 0


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
    global decision_active
    if decision.instance:
        decision_active = decision.instance.is_running

    # Debug
    global overlay_visible
    overlay_visible = overlay.is_visible
