# Global values

from tools import window_functions
from tools import overlay

from process import decision, detection


window_found = False
window_active = False
window_rect = None
overlay_visible = False

detection_active = False
decision_active = False

detections = None  # Set by detection.py


def update():
    global window_found
    window_found = window_functions.is_found()

    global window_active
    window_active = window_functions.is_active()

    global window_rect
    window_rect = window_functions.get_rect()

    global detection_active
    if detection.instance:
        detection_active = detection.instance.is_running

    global decision_active
    if decision.instance:
        decision_active = decision.instance.is_running

    global overlay_visible
    overlay_visible = overlay.is_visible
