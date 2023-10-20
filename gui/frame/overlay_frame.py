# GUI Section for Overlay

from tkinter import *
from tkinter.ttk import *

from gui import references
from tools import overlay


class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)
        #
        self.overlay_visible = Label(self, image=references.red_icon)
        self.overlay_visible.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Is Visible", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle Overlay", command=lambda: self.toggle_overlay()).grid(sticky=E, row=1, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()
        print(overlay.is_visible)


    def toggle_overlay(self):
        overlay.toggle_overlay()
        self.refresh()


    def refresh(self):
        self.overlay_visible.configure(image=(references.red_icon, references.green_icon)[overlay.is_visible])
