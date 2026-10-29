# Tests for the ` hotkey that toggles Botting, with the keyboard state and the window in front made up

import unittest
from tkinter import Tk
from unittest import mock

from data import values
from gui import references
from tools import hotkeys


class HotkeyTests(unittest.TestCase):
    def test_once_per_press(self):
        key = hotkeys.Hotkey(hotkeys.VK_OEM_3)
        states = iter([0, 0x8000, 0x8000, 0x8000, 0, 0x8001])  # Up, held for three polls, up, down again
        with mock.patch.object(hotkeys.user32, "GetAsyncKeyState", lambda vk: next(states)):
            self.assertEqual([key.pressed() for _ in range(6)], [False, True, False, False, False, True])


class BottingHotkeyTests(unittest.TestCase):
    def setUp(self):
        self.tk = Tk()
        self.tk.withdraw()
        self.addCleanup(self.tk.destroy)
        references.initialize_images()
        from gui.panel import process_panel
        from process import bot
        self.bot = mock.Mock(is_running=False)
        patcher = mock.patch.object(bot, "instance", self.bot)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.panel = process_panel.ProcessPanel(self.tk)

    def press(self, game_in_front, front=None):
        states = iter([0x8000, 0])  # Down on this poll, up on the next
        with mock.patch.object(hotkeys.user32, "GetAsyncKeyState", lambda vk: next(states)), \
                mock.patch.object(values, "window_active", game_in_front), mock.patch.object(hotkeys, "foreground", lambda: front):
            self.panel.check_hotkey()
            self.panel.check_hotkey()

    def test_toggles_botting_with_the_game_in_front(self):
        self.press(True)
        self.assertTrue(self.bot.is_running)
        self.press(True)
        self.assertFalse(self.bot.is_running)

    def test_toggles_with_the_bot_window_in_front(self):
        self.press(False, front=int(self.tk.wm_frame(), 16))
        self.assertTrue(self.bot.is_running)

    def test_ignored_in_other_programs(self):  # Typing ` elsewhere doesn't start the bot
        self.press(False, front=12345)
        self.assertFalse(self.bot.is_running)


if __name__ == "__main__":
    unittest.main()
