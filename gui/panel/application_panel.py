# GUI Section for Status

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values
from tools import window_functions
from tools.persistent import save_data


class ApplicationPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Application", borderwidth=1, relief=GROOVE)
        #
        self.window_name = Entry(self, textvariable=save_data.window_name.read(), font=references.var_font, width=30)
        self.window_name.grid(row=0, column=0, padx=15, pady=5, columnspan=2)
        self.window_name.bind('<KeyRelease>', self.on_window_name_change)
        self.window_name.insert(0, save_data.window_name.read())
        self.on_window_name_change(self)
        #
        self.window_found = Label(self, image=references.red_icon)
        self.window_found.grid(row=2, column=0, padx=15, pady=5)
        Label(self, text="Application Found", font=references.var_font).grid(sticky=W, row=2, column=1, padx=0, pady=0)
        #
        self.window_active = Label(self, image=references.red_icon)
        self.window_active.grid(row=3, column=0, padx=15, pady=5)
        Label(self, text="Window Active", font=references.var_font).grid(sticky=W, row=3, column=1, padx=0, pady=0)
        #
        self.grid_columnconfigure(1, weight=1, uniform="column")
        self.pack(fill=X)


    def on_window_name_change(self, event):
        save_data.window_name.save(self.window_name.get())
        window_functions.maple_name = self.window_name.get()


    def refresh(self):
        self.window_found.configure(image=(references.red_icon, references.green_icon)[values.window_found])
        self.window_active.configure(image=(references.red_icon, references.green_icon)[values.window_active])