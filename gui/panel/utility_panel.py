# GUI Section for Utility

from tkinter import *
from tkinter.ttk import *

from data import values
from tools import window_functions
from tools.persistent import save_data


class UtilityPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Utility", borderwidth=1, relief=GROOVE)
        #
        Button(self, text="Snap MS", command=lambda: self.snap_maple()).grid(sticky=W, row=0, column=0, padx=5, pady=5)
        Button(self, text="Snap Bot", command=lambda: self.snap_bot()).grid(sticky=W, row=0, column=1, padx=5, pady=5)
        #
        self.checkbox_state = BooleanVar(value=bool(save_data.snap_on_start.read()))
        self.checkbox = Checkbutton(self, text="On Start", variable=self.checkbox_state, command=self.on_snap_change)
        self.checkbox.grid(row=0, column=2, padx=5, pady=5)
        #
        # Label(self, text="Window Rect").grid(sticky=W, row=1, column=0, padx=10, pady=5)
        # self.window_rect_display = Label(self)
        # self.window_rect_display.grid(row=1, column=1, padx=10, pady=5)
        #
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        #
        if self.checkbox_state.get() is True:
            self.snap_maple()
            self.snap_bot()


    def on_snap_change(self):
        save_data.snap_on_start.save(self.checkbox_state.get())

    def snap_maple(self):
        window_functions.snap_maple_position()

    def snap_bot(self):
        window_functions.snap_bot_position()

    def refresh(self):
        pass
        # self.window_rect_display['text'] = str(values.window_rect)