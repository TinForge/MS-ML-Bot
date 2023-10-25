# GUI Section for Utility

from tkinter import *
from tkinter.ttk import *

from tools import values, window_functions


class UtilityPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Utility", borderwidth=1, relief=GROOVE)
        #
        Button(self, text="Show Window", command=lambda: self.show_window()).grid(sticky=W, row=0, column=0, padx=10, pady=5)
        #
        Label(self, text="Rect").grid(sticky=W, row=1, column=0, padx=10, pady=5)
        self.window_rect_display = Label(self)
        self.window_rect_display.grid(row=1, column=1, padx=10, pady=5)
        #
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        #


    def show_window(self):
        window_functions.set_rect()


    def refresh(self):
        self.window_rect_display['text'] = str(values.window_rect)