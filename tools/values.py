# Global values

from tools import window_functions

isWindowFound = False
isWindowActive = False
windowRect = None


def update():
    global isWindowFound
    global isWindowActive
    global windowRect
    isWindowFound = window_functions.is_found()
    isWindowActive = window_functions.is_active()
    windowRect = window_functions.get_rect()