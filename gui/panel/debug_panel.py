# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from data import values
from tools import overlay


class DebugPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Debug", borderwidth=1, relief=GROOVE)
        #
        self.window_rect_display = Label(self)
        self.window_rect_display.grid(sticky=W, row=0, column=0, padx=5, pady=5)
        Button(self, text="Show", command=lambda: self.toggle_window_rect()).grid(sticky=E, row=0, column=1, padx=5, pady=5)
        #
        self.grid_columnconfigure(0, weight=1)
        self.pack(fill=X)


    def toggle_window_rect(self):  # Draws the detected game area on the overlay
        values.show_window_rect = not values.show_window_rect
        if values.show_window_rect and not overlay.is_visible:
            overlay.enable_overlay()

    def refresh(self):
        rect = values.window_rect
        if rect is None:
            self.window_rect_display['text'] = "Window not found"
        else:
            self.window_rect_display['text'] = "%dx%d (%d, %d)" % (rect[2] - rect[0], rect[3] - rect[1], rect[0], rect[1])
