from mapletools import tools

isWindowFound = False
isWindowActive = False
windowRect = None


def update():
    global isWindowFound
    global isWindowActive
    global windowRect
    isWindowFound = tools.is_window_found()
    isWindowActive = tools.is_window_active()
    windowRect = tools.get_window_rect()
