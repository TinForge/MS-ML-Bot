# Functions for using Maplestory Window Applications

import ctypes
import win32gui
import win32con
import win32com
import win32com.client

windowName = "MapleLegends (Sep 10 2023)"


def get_instance():
    return win32gui.FindWindow(None, windowName)


def is_found():
    if get_instance() == 0:
        return False
    else:
        return True


def is_active():
    hwnd = ctypes.windll.user32.GetForegroundWindow() 
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    if buffer.value == windowName:
        return True
    else:
        return False


def get_rect():
    if is_found() is False:
        return False
    else:
        return win32gui.GetWindowRect(get_instance())


def set_rect():
    if is_found() is False:
        return False
    else:
        win32gui.SetWindowPos(get_instance(), 0, 0, 0, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)


def show():
    if is_found() is False:
        return
    else:
        shell = win32com.client.Dispatch("WScript.Shell")  # not sure if helps
        shell.SendKeys('%')
        # win32gui.SetForegroundWindow(try_get_window())
        ctypes.windll.user32.SetForegroundWindow(get_instance()) 



def main():
    if is_found() is False:
        print("Maplestory not found")
        exit()

    show()
    print(get_rect())  # (0, 0, 800, 600)


if __name__ == "__main__":
    main()