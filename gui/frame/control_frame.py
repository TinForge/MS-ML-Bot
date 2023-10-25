# GUI Section for Overlay

from tkinter import *
from tkinter.ttk import *

from gui import references
from tools import overlay
from tools import values
from process import detection
from process import decision


class ControlPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Control", borderwidth=1, relief=GROOVE)
        #
        self.detection_active = Label(self, image=references.red_icon)
        self.detection_active.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Model Detection", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle Process", command=lambda: self.toggle_detection()).grid(sticky=E, row=1, column=2, padx=0, pady=0)

        self.decision_active = Label(self, image=references.red_icon)
        self.decision_active.grid(row=2, column=0, padx=15, pady=5)
        Label(self, text="Bot Decision", font=references.var_font).grid(sticky=W, row=2, column=1, padx=0, pady=0)
        Button(self, text="Toggle Process", command=lambda: self.toggle_decision()).grid(sticky=E, row=2, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def toggle_detection(self):
        if detection.instance:
            detection.instance.is_running = not detection.instance.is_running

    def toggle_decision(self):
        if decision.instance:
            decision.instance.is_running = not decision.instance.is_running

    def refresh(self):
        self.detection_active.configure(image=(references.red_icon, references.green_icon)[values.detection_active])
        self.decision_active.configure(image=(references.red_icon, references.green_icon)[values.decision_active])
