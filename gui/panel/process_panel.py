# GUI Section for Control

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values
from process import calculations, detection, bot


class ProcessPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Processes", borderwidth=1, relief=GROOVE)
        #
        self.detection_active = Label(self, image=references.red_icon)
        self.detection_active.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Model Detection", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_detection()).grid(sticky=E, row=1, column=2, padx=0, pady=0)

        self.calculations_active = Label(self, image=references.red_icon)
        self.calculations_active.grid(row=2, column=0, padx=15, pady=5)
        Label(self, text="Data Calculations", font=references.var_font).grid(sticky=W, row=2, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_calculations()).grid(sticky=E, row=2, column=2, padx=0, pady=0)

        self.bot_active = Label(self, image=references.red_icon)
        self.bot_active.grid(row=3, column=0, padx=15, pady=5)
        Label(self, text="Botting", font=references.var_font).grid(sticky=W, row=3, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_botting()).grid(sticky=E, row=3, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def toggle_detection(self):
        if detection.instance:
            detection.instance.is_running = not detection.instance.is_running

    def toggle_calculations(self):
        if calculations.instance:
            calculations.instance.is_running = not calculations.instance.is_running

    def toggle_botting(self):
        if bot.instance:
            bot.instance.is_running = not bot.instance.is_running

    def refresh(self):
        self.detection_active.configure(image=(references.red_icon, references.green_icon)[values.detection_active])
        self.calculations_active.configure(image=(references.red_icon, references.green_icon)[values.calculations_active])
        self.bot_active.configure(image=(references.red_icon, references.green_icon)[values.bot_active])
