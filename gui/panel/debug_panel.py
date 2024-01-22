# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values
from tools import overlay


class DebugPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Debug", borderwidth=1, relief=GROOVE)

        self.iou_text = Label(self, text="Null")
        self.iou_text.grid(row=1, column=0, padx=15, pady=5, sticky=W)
        self.iou_slider = Scale(self, from_=0, to=1, orient="horizontal", command=self.on_iou_changed)
        self.iou_slider.set(values.model_iou)
        self.iou_slider.grid(row=1, column=1, padx=15, pady=5)

        self.conf_text = Label(self, text="Null")
        self.conf_text.grid(row=2, column=0, padx=15, pady=5, sticky=W)
        self.conf_slider = Scale(self, from_=0, to=1, orient="horizontal", command=self.on_conf_changed)
        self.conf_slider.set(values.model_conf)
        self.conf_slider.grid(row=2, column=1, padx=15, pady=5)

        self.debug1 = Label(self, text="Null")
        self.debug1.grid(row=3, column=0, padx=15, pady=5, sticky=W)

        self.debug2 = Label(self, text="Null")
        self.debug2.grid(row=4, column=0, padx=15, pady=5, sticky=W)

        self.debug3 = Label(self, text="Null")
        self.debug3.grid(row=3, column=1, padx=15, pady=5, sticky=E)

        self.debug4 = Label(self, text="Null")
        self.debug4.grid(row=4, column=1, padx=15, pady=5, sticky=E)

        self.debug5 = Label(self, text="Null")
        self.debug5.grid(row=5, column=0, padx=15, pady=5, sticky=W, columnspan=2)

        self.grid_columnconfigure(0, weight=1, uniform="column")
        self.grid_columnconfigure(1, weight=1, uniform="column")

        self.pack(fill=X)

    def on_iou_changed(self, value):
        values.model_iou = round(float(value), 2)

    def on_conf_changed(self, value):        
        values.model_conf = round(float(value), 2)


    def refresh(self):
        self.iou_text.configure(text="IOU: " + str(values.model_iou))
        self.conf_text.configure(text="CONF: " + str(values.model_conf))

        self.debug1.configure(text="Player" if values.debug_player is not None else "No Player")
        self.debug2.configure(text="Mob" if values.debug_mob is not None else "No Mob")
        self.debug5.configure(text="Action: " + str(values.debug_action))
        self.debug3.configure(text="Relative X: " + str(int(values.debug_x_distance)))
        self.debug4.configure(text="Relative Y: " + str(int(values.debug_y_distance)))