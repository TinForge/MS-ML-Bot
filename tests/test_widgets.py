# Tests for widget updates that only reach Tk when something changed

import unittest
from unittest import mock

from gui.widgets import update


class Widget:
    def __init__(self):
        self.configure = mock.Mock()


class UpdateTests(unittest.TestCase):
    def test_only_changes_reach_the_widget(self):  # Re-setting what's already shown made Tk redraw the window every pass
        w = Widget()
        update(w, text="HP 100", foreground="red")
        update(w, text="HP 100", foreground="red")
        update(w, text="HP 90", foreground="red")
        self.assertEqual(w.configure.call_args_list, [mock.call(text="HP 100", foreground="red"), mock.call(text="HP 90")])

    def test_images_compared_as_objects(self):
        w, image = Widget(), object()
        update(w, image=image)
        update(w, image=image)
        update(w, image="")
        self.assertEqual(w.configure.call_count, 2)


if __name__ == "__main__":
    unittest.main()
