import win32gui
import time
import win32com
import win32com.client
import ctypes
from ctypes import wintypes

windowName = "MapleLegends (Mar 12 2023)"


# 
def try_get_window():
    return win32gui.FindWindow(None, windowName)


def is_window_found():
    if try_get_window() == 0:
        return False
    else:
        return True


def is_window_active():
    hwnd = ctypes.windll.user32.GetForegroundWindow() 
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
    # print(buff.value)
    if buff.value == windowName:
        return True
    else:
        return False


def get_window_rect():
    if is_window_found() is False:
        return False
    else:
        return win32gui.GetWindowRect(try_get_window())


def show_window():
    if is_window_found() is False:
        return
    else:
        shell = win32com.client.Dispatch("WScript.Shell")  # not sure if helps
        shell.SendKeys('%')
        # win32gui.SetForegroundWindow(try_get_window())
        ctypes.windll.user32.SetForegroundWindow(try_get_window()) 




def main():
    if is_window_found() is False:
        print("Maplestory not found")
        exit()

    show_window()
    time.sleep(1)
    print(get_window_rect())  # (0, 0, 800, 600)




if __name__ == "__main__":
    main()