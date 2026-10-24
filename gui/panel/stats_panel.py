# GUI Section for HP/MP

from tkinter import *
from tkinter.ttk import *

from data import values

import time

drop_display_time = 1.5  # Seconds a drop stays visible


class DropTracker:  # Remembers recent decreases of a (current, max) value
    def __init__(self):
        self.last = None  # Last known current value
        self.drop = 0
        self.drop_time = 0

    def update(self, value):
        if value is None:  # Unknown reads are skipped, so flipping to/from unknown never counts as a drop
            return
        current = value[0]
        if self.last is not None and current < self.last:
            if self.visible_drop() == 0:
                self.drop = 0
            self.drop += self.last - current  # Drops in quick succession add up
            self.drop_time = time.time()
        self.last = current

    def visible_drop(self):
        if time.time() - self.drop_time < drop_display_time:
            return self.drop
        return 0


class StatsPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Stats", borderwidth=1, relief=GROOVE)
        #
        self.hp_tracker = DropTracker()
        self.mp_tracker = DropTracker()
        #
        Label(self, text="HP").grid(sticky=W, row=0, column=0, padx=10, pady=5)
        self.hp_text = Label(self)
        self.hp_text.grid(sticky=W, row=0, column=1, padx=5, pady=5)
        self.hp_drop = Label(self, foreground="red")
        self.hp_drop.grid(sticky=E, row=0, column=2, padx=10, pady=5)
        #
        Label(self, text="MP").grid(sticky=W, row=1, column=0, padx=10, pady=5)
        self.mp_text = Label(self)
        self.mp_text.grid(sticky=W, row=1, column=1, padx=5, pady=5)
        self.mp_drop = Label(self, foreground="red")
        self.mp_drop.grid(sticky=E, row=1, column=2, padx=10, pady=5)
        #
        self.grid_columnconfigure(1, weight=1)
        self.pack(fill=X)


    def refresh(self):
        self.refresh_stat(values.player_hp, self.hp_tracker, self.hp_text, self.hp_drop)
        self.refresh_stat(values.player_mp, self.mp_tracker, self.mp_text, self.mp_drop)

    def refresh_stat(self, value, tracker, text, drop):
        tracker.update(value)
        text.configure(text="%d / %d" % value if value is not None else "?")
        amount = tracker.visible_drop()
        drop.configure(text="▼ %d" % amount if amount > 0 else "")
