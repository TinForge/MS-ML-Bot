#  Functions for maplestory detection
import win32gui
import time
import win32com
import win32com.client

windowName = "MapleLegends (Nov 6 2022)"


def get_ms_window():
    return win32gui.FindWindow(None, windowName)


def is_ms_found():
    if get_ms_window() == 0:
        return False
    else:
        return True


def is_ms_enabled():
    if is_ms_found() is False:
        return False
    else:
        return win32gui.IsWindowEnabled(get_ms_window())
        return win32gui.IsWindowVisible(get_ms_window())


def get_ms_rect():
    if is_ms_found() is False:
        return False
    else:
        return win32gui.GetWindowRect(get_ms_window())


def show_ms():
    if is_ms_found() is False:
        return
    else:
        shell = win32com.client.Dispatch("WScript.Shell")  # Not sure if helps
        shell.SendKeys('%')
        win32gui.SetForegroundWindow(get_ms_window())




def main():
    # Tester
    if is_ms_found() is False:
        print("Maplestory not found")
        exit()

    print("is enabled", is_ms_enabled())
    show_ms()
    time.sleep(1)
    print(get_ms_rect())  # (0, 0, 800, 600)


if __name__ == "__main__":
    main()