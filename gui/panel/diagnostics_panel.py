# GUI Section for Diagnostics

from tkinter import *
from tkinter.ttk import *

from gui import references
from gui.widgets import update
from data import values
from tools import overlay


class DiagnosticsPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Diagnostics", borderwidth=1, relief=GROOVE)

        self.iou_text = Label(self, text="Null")
        self.iou_text.grid(row=1, column=0, padx=10, pady=5, sticky=W)
        self.iou_slider = Scale(self, from_=0, to=1, orient="horizontal", command=self.on_iou_changed)
        self.iou_slider.set(values.model_iou)
        self.iou_slider.grid(row=1, column=1, padx=10, pady=5)

        self.conf_text = Label(self, text="Null")
        self.conf_text.grid(row=2, column=0, padx=10, pady=5, sticky=W)
        self.conf_slider = Scale(self, from_=0, to=1, orient="horizontal", command=self.on_conf_changed)
        self.conf_slider.set(values.model_conf)
        self.conf_slider.grid(row=2, column=1, padx=10, pady=5)

        # Column 1

        self.debug1 = Label(self, text="Null")
        self.debug1.grid(row=3, column=0, padx=10, pady=5, sticky=W)

        self.debug2 = Label(self, text="Null")
        self.debug2.grid(row=4, column=0, padx=10, pady=5, sticky=W)

        self.debug3 = Label(self, text="Null")
        self.debug3.grid(row=5, column=0, padx=10, pady=5, sticky=W)

        self.debug4 = Label(self, text="Null")
        self.debug4.grid(row=6, column=0, padx=10, pady=5, sticky=W)

        self.debugX = Label(self, text="Null")
        self.debugX.grid(row=7, column=0, padx=10, pady=5, sticky=W)

        # Column 2

        self.debug5 = Label(self, text="Null")
        self.debug5.grid(row=3, column=1, padx=10, pady=5, sticky=E)

        self.debug6 = Label(self, text="Null")
        self.debug6.grid(row=4, column=1, padx=10, pady=5, sticky=E)

        self.debug7 = Label(self, text="Null")
        self.debug7.grid(row=5, column=1, padx=10, pady=5, sticky=E)
        
        self.debug8 = Label(self, text="Null")
        self.debug8.grid(row=6, column=1, padx=10, pady=5, sticky=E)

        self.grid_columnconfigure(0, weight=0, minsize=150)
        self.grid_columnconfigure(1, weight=1)

        self.pack(fill=X)

    def on_iou_changed(self, value):
        values.model_iou = round(float(value), 2)

    def on_conf_changed(self, value):        
        values.model_conf = round(float(value), 2)


    def refresh(self):
        update(self.iou_text, text="IOU: " + str(values.model_iou))
        update(self.conf_text, text="CONF: " + str(values.model_conf))

        update(self.debug1, text="State: " + str(values.debug_state))
        update(self.debug2, text="Action: " + str(values.debug_action))
        update(self.debug3, text="Relative X: " + str(int(values.debug_x_distance)))
        update(self.debug4, text="Relative Y: " + str(int(values.debug_y_distance)))

        update(self.debug5, text="Player" if values.debug_player is not None else "No Player")
        update(self.debug6, text="Platform" if values.debug_platform is not None else "No Platform")
        update(self.debug7, text="Mob" if values.debug_mob is not None else "No Mob")
        update(self.debug8, text="Path" if values.debug_path is not None else "No Path")
        update(self.debugX, text="Ladder" if values.debug_on_ladder is True else "No Ladder")