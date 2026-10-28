# Keyboard shortcuts read while the game is in front, by polling the key's state from the GUI loop (the key still reaches the game)

import ctypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

VK_OEM_3 = 0xC0  # The ` key (left of 1 on a US keyboard)


class Hotkey:
    def __init__(self, vk):
        self.vk = vk
        self.down = False

    def pressed(self):  # True once each time the key goes down, however long it's held
        down = bool(user32.GetAsyncKeyState(self.vk) & 0x8000)
        fresh = down and not self.down
        self.down = down
        return fresh


def foreground():  # Handle of the window in front
    return user32.GetForegroundWindow()
