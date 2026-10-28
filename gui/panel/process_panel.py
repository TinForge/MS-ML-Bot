# GUI Section for Control

from tkinter import *
from tkinter.ttk import *

from gui import references
from gui.widgets import update
from data import values
from process import calculations, detection, bot
from tools import hotkeys

BOTTING_KEY = hotkeys.VK_OEM_3  # ` toggles Botting while the game or this window is in front


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
        Label(self, text="Botting  ( ` )", font=references.var_font).grid(sticky=W, row=3, column=1, padx=0, pady=0)
        Button(self, text="Toggle", command=lambda: self.toggle_botting()).grid(sticky=E, row=3, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)
        self.botting_hotkey = hotkeys.Hotkey(BOTTING_KEY)


    def toggle_detection(self):
        if detection.instance:
            detection.instance.is_running = not detection.instance.is_running

    def toggle_calculations(self):
        if calculations.instance:
            calculations.instance.is_running = not calculations.instance.is_running

    def toggle_botting(self):
        if bot.instance:
            bot.instance.is_running = not bot.instance.is_running

    def check_hotkey(self):  # Only with the game or the bot in front, so typing ` elsewhere doesn't start it
        if self.botting_hotkey.pressed() and (values.window_active or self.bot_in_front()):
            self.toggle_botting()

    def bot_in_front(self):
        front = hotkeys.foreground()
        return any(front == int(w.wm_frame(), 16) for w in (self.winfo_toplevel(), *self.winfo_toplevel().winfo_children()) if hasattr(w, "wm_frame"))

    def refresh(self):
        self.check_hotkey()
        if values.model_loading:  # Yellow while the model loads on first use
            update(self.detection_active, image=references.yellow_icon)
        else:
            update(self.detection_active, image=(references.red_icon, references.green_icon)[values.detection_active])
        update(self.calculations_active, image=(references.red_icon, references.green_icon)[values.calculations_active])
        update(self.bot_active, image=(references.red_icon, references.green_icon)[values.bot_active])
