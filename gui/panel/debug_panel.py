# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from gui import references
from tools import overlay, values


class DebugPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Debug", borderwidth=1, relief=GROOVE)

        self.overlay_visible = Label(self, image=references.red_icon)
        self.overlay_visible.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Detection Overlay", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_overlay()).grid(sticky=E, row=1, column=2, padx=0, pady=0)

        self.debug1 = Label(self, text="Example 1")
        self.debug1.grid(row=2, column=0, padx=15, pady=5)

        self.debug2 = Label(self, text="Example 2")
        self.debug2.grid(row=3, column=0, padx=15, pady=5)

        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def toggle_overlay(self):
        overlay.toggle_overlay()


    def refresh(self):
        if overlay.instance is not None:
            if values.detected_instances is not None:
                overlay.instance.display_rects(values.detected_instances)

        self.overlay_visible.configure(image=(references.red_icon, references.green_icon)[overlay.is_visible])
        if values.debug_monster is not None:
            self.debug1.configure(text=values.debug_action)
            self.debug2.configure(text=str(values.debug_distance))
            pass