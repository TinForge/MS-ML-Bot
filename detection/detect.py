import win32gui
import time


windowName = "MapleLegends (Nov 6 2022)"


def MapleWindow():
    return win32gui.FindWindow(None, windowName)


def IsMapleFound():
    if MapleWindow() == 0:
        return False
    else:
        return True


def IsMapleEnabled():
    if IsMapleFound() is False:
        return False
    else:
        return win32gui.IsWindowEnabled(MapleWindow())
        return win32gui.IsWindowVisible(MapleWindow())


def GetMapleRect():
    if IsMapleFound() is False:
        return False
    else:
        return win32gui.GetWindowRect(MapleWindow())


def ShowMaple():
    if IsMapleFound() is False:
        return
    else:
        win32gui.SetForegroundWindow(MapleWindow())



def main():
    if IsMapleFound() is False:
        print("Maplestory not found")
        exit()

    print("is enabled", IsMapleEnabled())
    ShowMaple()
    time.sleep(1)
    print(GetMapleRect())  # (0, 0, 800, 600)


if __name__ == "__main__":
    main()