from mapletools import tools

isWindowFound = False
isWindowEnabled = False
windowRect = None


def update():
    global isWindowFound
    global isWindowEnabled
    global windowRect
    isWindowFound = tools.IsWindowFound()
    isWindowEnabled = tools.IsWindowVisible()
    windowRect = tools.GetRect()
