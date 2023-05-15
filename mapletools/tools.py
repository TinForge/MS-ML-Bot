import win32gui
import time
import win32com
import win32com.client

windowName = "MapleLegends (Mar 12 2023)"


# 
def GetWindow():
    return win32gui.FindWindow(None, windowName)


def IsWindowFound():
    if GetWindow() == 0:
        return False
    else:
        return True


def IsWindowVisible():
    if IsWindowFound() is False:
        return False
    if False:
        if win32gui.IsWindowEnabled(GetWindow()) == 0:
            return False
        else:
            return True
    if True:
        if win32gui.IsWindowVisible(GetWindow()) == 0:
            return False
        else:
            return True


def GetRect():
    if IsWindowFound() is False:
        return False
    else:
        return win32gui.GetWindowRect(GetWindow())


def ShowWindow():
    if IsWindowFound() is False:
        return
    else:
        shell = win32com.client.Dispatch("WScript.Shell")  # not sure if helps
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(GetWindow())



def main():
    if IsWindowFound() is False:
        print("Maplestory not found")
        exit()

    print("is enabled", IsWindowVisible())
    ShowWindow()
    time.sleep(1)
    print(GetRect())  # (0, 0, 800, 600)


if __name__ == "__main__":
    main()