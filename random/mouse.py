from turtle import left, right
import pyautogui


def get_mouse_pos():
    return pyautogui.position()


def get_screen_size():
    return pyautogui.size()


def is_coord_on_screen(x, y):
    return pyautogui.onScreen(x, y)


def get_left_click():
    return pyautogui.click(button=left)


def get_right_click():
    return pyautogui.click(button=right)
