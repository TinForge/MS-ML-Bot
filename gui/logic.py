#  Reads values from detect
from detection import detect

isMapleFound = False
isMapleEnabled = False
mapleRect = None


def update():
    global isMapleFound
    global isMapleEnabled
    global mapleRect
    isMapleFound = detect.is_ms_found()
    isMapleEnabled = detect.is_ms_enabled()
    mapleRect = detect.get_ms_rect()
