# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from gui import references
from data import values
from tools import overlay


class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)

        self.overlay_visible = Label(self, image=references.red_icon)
        self.overlay_visible.grid(row=1, column=0, padx=15, pady=5)
        Button(self, text="Toggle", command=lambda: self.toggle_overlay()).grid(sticky=E, row=1, column=2, padx=0, pady=0)

        OPTIONS = ["Raw Detections", "Averaged Detections", "Targets", "Velocities", "Platforms"]
        selected_options = []
        self.listbox = Listbox(self, selectmode=MULTIPLE, height=len(OPTIONS))
        for option in OPTIONS:
            self.listbox.insert(END, option)

        def handle_selection(event):
            selected_options.clear()
            selected_indices = self.listbox.curselection()
            for index in selected_indices:
                selected_options.append(OPTIONS[index])
        self.listbox.bind("<<ListboxSelect>>", handle_selection)

        self.listbox.grid(row=1, column=1, pady=5, sticky="ew")  # ew expands east-west

        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def toggle_overlay(self):
        overlay.toggle_overlay()


    def refresh(self):
        if overlay.instance is not None:
            if values.detected_instances is not None:
                overlay.instance.display_rects(values.detected_instances)

        self.overlay_visible.configure(image=(references.red_icon, references.green_icon)[overlay.is_visible])
