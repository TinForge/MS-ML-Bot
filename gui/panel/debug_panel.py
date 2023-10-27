# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values
from tools import overlay


class DebugPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Debug", borderwidth=1, relief=GROOVE)

        self.overlay_visible = Label(self, image=references.red_icon)
        self.overlay_visible.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Detection Overlay", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_overlay()).grid(sticky=E, row=1, column=2, padx=0, pady=0)

        self.debug1 = Label(self, text="Null")
        self.debug1.grid(row=2, column=1, padx=15, pady=5)

        self.debug2 = Label(self, text="Null")
        self.debug2.grid(row=3, column=1, padx=15, pady=5)

        self.debug3 = Label(self, text="Null")
        self.debug3.grid(row=4, column=1, padx=15, pady=5)

        self.debug4 = Label(self, text="Null")
        self.debug4.grid(row=5, column=1, padx=15, pady=5)

        self.debug5 = Label(self, text="Null")
        self.debug5.grid(row=6, column=1, padx=15, pady=5)

        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def toggle_overlay(self):
        overlay.toggle_overlay()


    def refresh(self):
        if overlay.instance is not None:
            if values.detected_instances is not None:
                overlay.instance.display_rects(values.detected_instances)

        self.overlay_visible.configure(image=(references.red_icon, references.green_icon)[overlay.is_visible])

        self.debug1.configure(text="Player" if values.debug_player is not None else "No Player")
        self.debug2.configure(text="Mob" if values.debug_mob is not None else "No Mob")
        self.debug3.configure(text="Relative X: " + str(int(values.debug_x_distance)))
        self.debug4.configure(text="Relative Y: " + str(int(values.debug_y_distance)))
        self.debug5.configure(text="Action: " + str(values.debug_action))