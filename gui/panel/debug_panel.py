# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values
from tools import overlay


class DebugPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Debug", borderwidth=1, relief=GROOVE)

        self.debug1 = Label(self, text="Null")
        self.debug1.grid(row=1, column=0, padx=15, pady=5, sticky="W")

        self.debug2 = Label(self, text="Null")
        self.debug2.grid(row=2, column=0, padx=15, pady=5, sticky="W")

        self.debug3 = Label(self, text="Null")
        self.debug3.grid(row=1, column=1, padx=15, pady=5, sticky="W")

        self.debug4 = Label(self, text="Null")
        self.debug4.grid(row=2, column=1, padx=15, pady=5, sticky="W")

        self.debug5 = Label(self, text="Null")
        self.debug5.grid(row=3, column=0, padx=15, pady=5, sticky="W")

        self.pack(fill=X)


    def refresh(self):
        self.debug1.configure(text="Player" if values.debug_player is not None else "No Player")
        self.debug2.configure(text="Mob" if values.debug_mob is not None else "No Mob")
        self.debug3.configure(text="Relative X: " + str(int(values.debug_x_distance)))
        self.debug4.configure(text="Relative Y: " + str(int(values.debug_y_distance)))
        self.debug5.configure(text="Action: " + str(values.debug_action))