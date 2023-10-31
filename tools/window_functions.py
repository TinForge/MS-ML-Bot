# Functions for using Maplestory Window Applications

import ctypes
import win32gui
import win32con
import win32com
import win32com.client

maple_name = "MapleLegends (Sep 10 2023)"
bot_name = "Maplestory ML Bot"


def get_maple_window():
    return win32gui.FindWindow(None, maple_name)


def is_maple_found():
    if get_maple_window() == 0:
        return False
    else:
        return True


def is_maple_active():
    hwnd = ctypes.windll.user32.GetForegroundWindow() 
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buffer, length + 1)
    if buffer.value == maple_name:
        return True
    else:
        return False


def get_maple_position():
    if is_maple_found() is False:
        return False
    else:
        return win32gui.GetWindowRect(get_maple_window())


def snap_maple_position():
    if is_maple_found() is False:
        return False
    else:
        win32gui.SetWindowPos(get_maple_window(), 0, 0, 0, 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)


def show_maple():
    if is_maple_found() is False:
        return
    else:
        shell = win32com.client.Dispatch("WScript.Shell")  # not sure if helps
        shell.SendKeys('%')
        # win32gui.SetForegroundWindow(try_get_window())
        ctypes.windll.user32.SetForegroundWindow(get_maple_window()) 


def snap_bot_position():
    if is_maple_found() is True:
        rect = get_maple_position()
        win32gui.SetWindowPos(win32gui.FindWindow(None, bot_name), 0, rect[2], rect[1], 0, 0, win32con.SWP_NOZORDER | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)


def main():
    if is_maple_found() is False:
        print("Maplestory not found")
        exit()

    show_maple()
    print(get_maple_position())  # (0, 0, 800, 600)


if __name__ == "__main__":
    main()