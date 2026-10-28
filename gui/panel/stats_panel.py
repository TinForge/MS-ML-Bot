# GUI Section for HP/MP

from tkinter import *
from tkinter.ttk import *

from gui import references
from gui.widgets import update
from data import config, values
from tools import keyboard
from tools.persistent import save_data

import time

drop_display_time = config.drop_display_time  # Seconds a drop stays visible
potion_display_time = config.potion_display_time  # Seconds the potion indicator stays visible
value_width = 11  # Characters reserved so the row doesn't shift as text changes, e.g. "29999/30000"
drop_width = 6  # e.g. "▼ 9999"


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
        Label(self, text="Potion at").grid(sticky=W, row=0, column=3, padx=2)
        Label(self, text="Key").grid(row=0, column=4, padx=2)
        #
        Label(self, text="HP").grid(sticky=W, row=1, column=0, padx=(10, 5), pady=5)
        self.hp_text = Label(self, width=value_width)
        self.hp_text.grid(sticky=W, row=1, column=1, pady=5)
        self.hp_drop = Label(self, foreground="red", width=drop_width, anchor=E, compound=LEFT)  # Also shows the potion indicator
        self.hp_drop.grid(sticky=E, row=1, column=2, padx=2, pady=5)
        self.add_potion_inputs(1, "hp", save_data.hp_potion_threshold, save_data.hp_potion_key)
        #
        Label(self, text="MP").grid(sticky=W, row=2, column=0, padx=(10, 5), pady=5)
        self.mp_text = Label(self, width=value_width)
        self.mp_text.grid(sticky=W, row=2, column=1, pady=5)
        self.mp_drop = Label(self, foreground="red", width=drop_width, anchor=E, compound=LEFT)
        self.mp_drop.grid(sticky=E, row=2, column=2, padx=2, pady=5)
        self.add_potion_inputs(2, "mp", save_data.mp_potion_threshold, save_data.mp_potion_key)
        #
        Label(self, text="EXP").grid(sticky=W, row=3, column=0, padx=(10, 5), pady=5)
        self.exp_text = Label(self)
        self.exp_text.grid(sticky=W, row=3, column=1, pady=5)
        self.exp_gain = Label(self, foreground="green", width=drop_width, anchor=E)  # Each gain, which EXP Kill Check takes for a kill
        self.exp_gain.grid(sticky=E, row=3, column=2, padx=2, pady=5)
        self.exp_last, self.exp_gained, self.exp_gain_time = None, 0, 0
        #
        self.grid_columnconfigure(1, weight=1)
        self.pack(fill=X)


    def add_potion_inputs(self, row, stat, threshold_file, key_file):  # Threshold entry and key picker, saved on change
        threshold = StringVar(value=threshold_file.read())
        Entry(self, textvariable=threshold, width=5).grid(row=row, column=3, padx=2, pady=5)

        def on_threshold_change(*args):
            text = threshold.get().strip()
            setattr(values, stat + "_potion_threshold", int(text) if text.isdigit() else 0)  # Blank or invalid turns it off
            threshold_file.save(text)
        threshold.trace_add("write", on_threshold_change)
        on_threshold_change()

        key = StringVar(value=key_file.read() if key_file.read() in keyboard.KEY_NAMES else "Delete")
        Combobox(self, textvariable=key, values=list(keyboard.KEY_NAMES), state="readonly", width=9).grid(row=row, column=4, padx=2, pady=5)

        def on_key_change(*args):
            setattr(values, stat + "_potion_key", key.get())
            key_file.save(key.get())
        key.trace_add("write", on_key_change)
        on_key_change()


    def refresh(self):
        self.refresh_stat("HP", values.player_hp, self.hp_tracker, self.hp_text, self.hp_drop)
        self.refresh_stat("MP", values.player_mp, self.mp_tracker, self.mp_text, self.mp_drop)
        self.refresh_exp(values.player_exp)

    def refresh_exp(self, value):
        update(self.exp_text, text="%d (%.2f%%)" % value if value is not None else "?")
        if value is not None:
            if self.exp_last is not None and value[0] > self.exp_last:
                self.exp_gained, self.exp_gain_time = value[0] - self.exp_last, time.time()
            self.exp_last = value[0]
        shown = time.time() - self.exp_gain_time < drop_display_time
        update(self.exp_gain, text="▲ %d" % self.exp_gained if shown else "")

    def refresh_stat(self, stat, value, tracker, text, drop):
        tracker.update(value)
        update(text, text="%d/%d" % value if value is not None else "?")
        amount = tracker.visible_drop()
        potion_used = time.time() - values.last_potion_time[stat] < potion_display_time
        update(drop, text="▼ %d" % amount if amount > 0 else "", image=references.green_icon if potion_used else "")  # Green dot for a moment after a potion
