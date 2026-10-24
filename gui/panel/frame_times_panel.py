# GUI Section for Frame Times

from tkinter import *
from tkinter.ttk import *

from tools import timer

# (timer name, display name); stages of a detection frame, then its total
STAGES = [("Grab", "Screen Grab"), ("Inference", "Inference"), ("Stats", "HP/MP Read"), ("Player", "Player Find")]
TOTAL = ("Detection", "Total per Frame")


class FrameTimesPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Frame Times", borderwidth=1, relief=GROOVE)
        #
        self.time_labels = {}
        for row, (name, display_name) in enumerate(STAGES):
            self.add_row(row, name, display_name)
        Separator(self, orient=HORIZONTAL).grid(row=len(STAGES), column=0, columnspan=2, sticky=EW, padx=10, pady=2)
        self.add_row(len(STAGES) + 1, *TOTAL)
        #
        self.grid_columnconfigure(1, weight=1)
        self.pack(fill=X)


    def add_row(self, row, name, display_name):
        Label(self, text=display_name).grid(sticky=W, row=row, column=0, padx=10, pady=2)
        self.time_labels[name] = Label(self)
        self.time_labels[name].grid(sticky=E, row=row, column=1, padx=10, pady=2)

    def refresh(self):
        for name, label in self.time_labels.items():
            ms = timer.get(name)
            label.configure(text="%.1f ms" % ms if ms is not None else "-")
