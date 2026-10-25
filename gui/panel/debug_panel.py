# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

import numpy as np
import PIL.Image
import PIL.ImageTk

from data import values
from tools import overlay

name_scale = 2  # The name is shown as its pixels from the status bar, scaled up to be readable


def text_image(pixels, scale):  # Bool text pixels as dark text on a transparent image
    rgba = np.zeros(pixels.shape + (4,), dtype=np.uint8)
    rgba[pixels] = (30, 30, 30, 255)
    image = PIL.Image.fromarray(rgba).resize((pixels.shape[1] * scale, pixels.shape[0] * scale), PIL.Image.NEAREST)
    return PIL.ImageTk.PhotoImage(image)


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
        self.map_display = Label(self, compound=TOP, anchor=W, justify=LEFT)  # Map name image, then the player's dot on the minimap
        self.map_display.grid(sticky=W, row=2, column=0, padx=5, pady=5)
        Button(self, text="Show", command=lambda: self.toggle_minimap()).grid(sticky=E, row=2, column=1, padx=5, pady=5)
        self.map_image = None
        self.map_id = None
        #
        self.recording_display = Label(self)  # Recorded platforms and ladders on this map
        self.recording_display.grid(sticky=W, row=3, column=0, padx=5, pady=5)
        self.record_button = Button(self, text="Record", command=lambda: self.toggle_recording())
        self.record_button.grid(sticky=E, row=3, column=1, padx=5, pady=5)
        self.state_display = Label(self)  # Ground / Ladder / Air, or what mapping is still waiting for
        self.state_display.grid(sticky=W, row=4, column=0, padx=5, pady=5)
        Button(self, text="Show", command=lambda: self.toggle_platforms()).grid(sticky=E, row=4, column=1, padx=5, pady=5)
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

    def toggle_minimap(self):  # Draws the minimap's map area and the player's dot on the overlay
        values.show_minimap = not values.show_minimap
        if values.show_minimap and not overlay.is_visible:
            overlay.enable_overlay()

    def toggle_recording(self):  # Records the platforms and ladders the player walks and climbs
        values.record_platforms = not values.record_platforms
        self.record_button.configure(text="Stop" if values.record_platforms else "Record")

    def toggle_platforms(self):  # Draws the recorded platforms, ladders and the player's feet on the overlay
        values.show_platforms = not values.show_platforms
        if values.show_platforms and not overlay.is_visible:
            overlay.enable_overlay()

    def refresh(self):
        rect = values.window_rect
        if rect is None:
            self.window_rect_display['text'] = "Window not found"
        else:
            self.window_rect_display['text'] = "%dx%d (%d, %d)" % (rect[2] - rect[0], rect[3] - rect[1], rect[0], rect[1])
        self.refresh_player()
        self.refresh_minimap()
        self.refresh_mapping()

    def refresh_player(self):
        name = values.player_name
        if name is None:
            self.name_image = self.name_pixels = None
            self.player_display.configure(image="", text="Name not found")
            return
        if self.name_pixels is None or not np.array_equal(name, self.name_pixels):  # Only rebuild the image when the name changes
            self.name_pixels = name
            self.name_image = text_image(name, name_scale)
        player = values.player_rect
        if player is not None:
            position = "  (%d, %d)" % ((player[0] + player[2]) / 2, player[3])
        else:
            position = "  not on screen" if values.show_player_rect else ""  # Only searched for while shown or detecting
        self.player_display.configure(image=self.name_image, text=position)

    def refresh_minimap(self):
        m = values.minimap
        if m is None:
            self.map_image = self.map_id = None
            self.map_display.configure(image="", text="Minimap not found")
            return
        if m.map_id != self.map_id:  # Only rebuild the name image when the map changes
            self.map_id = m.map_id
            self.map_image = text_image(m.name, 1) if m.name is not None else ""
        width, height = m.size
        dot = "dot (%d, %d) of %dx%d" % (m.player[0], m.player[1], width, height) if m.player is not None else "dot not visible"
        text = "%s, %d other players" % (dot, len(m.others))
        if m.position is not None:  # Stays the same while the minimap scrolls
            text += "\nmap position (%d, %d)" % m.position
        self.map_display.configure(image=self.map_image, text=text)

    def refresh_mapping(self):
        mapper = values.mapper
        if mapper is None or mapper.calibration is None:
            self.recording_display.configure(text="Platforms: no map yet")
            self.state_display.configure(text="")
            return
        scale = mapper.calibration.scale
        self.recording_display.configure(text="Platforms: %d, ladders: %d%s" % (len(mapper.lines), len(mapper.ladders), ", scale %.1f" % scale if scale else ""))
        if not (values.record_platforms or values.show_platforms):
            state = "Map state: off"
        elif scale is None:
            state = "Calibrating: walk around a bit"
        elif mapper.feet is None:
            state = "Waiting for player and minimap"
        else:
            state = "Map state: %s at (%d, %d)" % (mapper.state or "...", mapper.feet[0], mapper.feet[1])
        self.state_display.configure(text=state)
