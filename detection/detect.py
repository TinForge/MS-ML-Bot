import win32gui
import time


def main():
    # hwnd = win32gui.FindWindow("MapleStoryClass", None)
    hwnd = win32gui.FindWindow(None, "MapleLegends (Nov 6 2022)")

    if hwnd == 0:
        print("Maplestory not found")
        exit()
    else:
        print(hwnd)


    print("is showing", win32gui.IsWindowVisible(hwnd))
    print("is enabled", win32gui.IsWindowEnabled(hwnd))
    print("is iconic", win32gui.IsIconic(hwnd))

    # Having trouble consistently showing the window
    # win32gui.ShowWindow(hwnd, 6)
    time.sleep(0.2)
    # win32gui.ShowWindow(hwnd, 9)
    time.sleep(0.2)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.2)
    # win32gui.UpdateWindow(hwnd)

    window_rect = win32gui.GetWindowRect(hwnd)
    print(window_rect)
    # (0, 0, 800, 600)


if __name__ == "__main__":
    main()