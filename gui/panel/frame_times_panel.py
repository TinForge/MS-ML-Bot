# GUI Section for Frame Times

from tkinter import *
from tkinter.ttk import *

from gui.widgets import update
from tools import timer

# (timer name, display name); each thread's stages, then its total. They run side by side: detection on one frame while the stats
# thread reads the one before, so the detection total is what sets the frame rate
GROUPS = [
    ([("Grab", "Screen Grab"), ("Inference", "Inference")], ("Detection", "Detection per Frame")),
    ([("Player", "Player Find"), ("Mapping", "Mapping"), ("Stats", "HP/MP Read"), ("Minimap", "Minimap")], ("Stats frame", "Stats per Frame")),
]


class FrameTimesPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Frame Times", borderwidth=1, relief=GROOVE)
        #
        self.time_labels = {}
        row = 0
        for stages, total in GROUPS:
            for name, display_name in stages:
                self.add_row(row, name, display_name)
                row += 1
            Separator(self, orient=HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky=EW, padx=10, pady=2)
            self.add_row(row + 1, *total)
            self.grid_rowconfigure(row + 2, minsize=12)  # A gap before the next group
            row += 3
        Label(self, text="Detection Rate").grid(sticky=W, row=row, column=0, padx=10, pady=2)
        self.rate_label = Label(self)
        self.rate_label.grid(sticky=E, row=row, column=1, padx=10, pady=2)
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
            update(label, text="%.1f ms" % ms if ms is not None else "-")
        loop = timer.get("Detection loop")
        update(self.rate_label, text="%.0f fps" % (1000 / loop) if loop else "-")
