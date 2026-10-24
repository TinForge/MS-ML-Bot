# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

import numpy as np
import PIL.Image
import PIL.ImageTk

from data import values
from tools import overlay

name_scale = 2  # The name is shown as its pixels from the status bar, scaled up to be readable


class DebugPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Debug", borderwidth=1, relief=GROOVE)
        #
        self.window_rect_display = Label(self)
        self.window_rect_display.grid(sticky=W, row=0, column=0, padx=5, pady=5)
        Button(self, text="Show", command=lambda: self.toggle_window_rect()).grid(sticky=E, row=0, column=1, padx=5, pady=5)
        #
        self.player_display = Label(self, compound=LEFT)  # Name image, then position text
        self.player_display.grid(sticky=W, row=1, column=0, padx=5, pady=5)
        Button(self, text="Show", command=lambda: self.toggle_player_rect()).grid(sticky=E, row=1, column=1, padx=5, pady=5)
        self.name_image = None
        self.name_pixels = None
        #
        self.grid_columnconfigure(0, weight=1)
        self.pack(fill=X)


    def toggle_window_rect(self):  # Draws the detected game area on the overlay
        values.show_window_rect = not values.show_window_rect
        if values.show_window_rect and not overlay.is_visible:
            overlay.enable_overlay()

    def toggle_player_rect(self):  # Draws the player found by their nametag on the overlay
        values.show_player_rect = not values.show_player_rect
        if values.show_player_rect and not overlay.is_visible:
            overlay.enable_overlay()

    def refresh(self):
        rect = values.window_rect
        if rect is None:
            self.window_rect_display['text'] = "Window not found"
        else:
            self.window_rect_display['text'] = "%dx%d (%d, %d)" % (rect[2] - rect[0], rect[3] - rect[1], rect[0], rect[1])
        self.refresh_player()

    def refresh_player(self):
        name = values.player_name
        if name is None:
            self.name_image = self.name_pixels = None
            self.player_display.configure(image="", text="Name not found")
            return
        if self.name_pixels is None or not np.array_equal(name, self.name_pixels):  # Only rebuild the image when the name changes
            self.name_pixels = name
            pixels = np.zeros(name.shape + (4,), dtype=np.uint8)
            pixels[name] = (30, 30, 30, 255)  # Dark text on a transparent background
            image = PIL.Image.fromarray(pixels).resize((name.shape[1] * name_scale, name.shape[0] * name_scale), PIL.Image.NEAREST)
            self.name_image = PIL.ImageTk.PhotoImage(image)
        player = values.player_rect
        if player is not None:
            position = "  (%d, %d)" % ((player[0] + player[2]) / 2, player[3])
        else:
            position = "  not on screen" if values.show_player_rect else ""  # Only searched for while shown or detecting
        self.player_display.configure(image=self.name_image, text=position)
