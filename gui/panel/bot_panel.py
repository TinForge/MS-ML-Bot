# GUI Section for Control

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values


class BotPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Bot", borderwidth=1, relief=GROOVE)
        #
        self.looting_active = Label(self, image=references.red_icon)
        self.looting_active.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Auto Looting", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_looting()).grid(sticky=E, row=1, column=2, padx=0, pady=0)
        #
        self.random_behaviour = Label(self, image=references.red_icon)
        self.random_behaviour.grid(row=2, column=0, padx=15, pady=5)
        Label(self, text="Random Behaviour", font=references.var_font).grid(sticky=W, row=2, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_random_behaviour()).grid(sticky=E, row=2, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def toggle_looting(self):
        values.looting_active = not values.looting_active

    def toggle_random_behaviour(self):
        values.randomizer_active = not values.randomizer_active

    def refresh(self):
        self.looting_active.configure(image=(references.red_icon, references.green_icon)[values.looting_active])
        self.random_behaviour.configure(image=(references.red_icon, references.green_icon)[values.randomizer_active])
