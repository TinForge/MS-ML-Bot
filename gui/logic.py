from detection import detect

isMapleFound = False
isMapleEnabled = False
mapleRect = None


def update():
    global isMapleFound
    global isMapleEnabled
    global mapleRect
    isMapleFound = detect.IsMapleFound()
    isMapleEnabled = detect.IsMapleEnabled()
    mapleRect = detect.GetMapleRect()

