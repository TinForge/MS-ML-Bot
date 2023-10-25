# GUI layout for main page

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.frame import control_frame, overlay_frame, status_frame, test_frame
from tools import values
from process import detection


class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        self.app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        #
        Label(self, text="Main Page", font='bold').pack(pady=10)
        Button(self, text="Inference", command=lambda: self.run_inference()).pack()
        #
        self.statusPanel = status_frame.StatusPanel(self)
        self.controlPanel = control_frame.ControlPanel(self)
        self.overlayPanel = overlay_frame.OverlayPanel(self)
        self.testPanel = test_frame.TestPanel(self)
        #

    # Need to move this to OverlayPanel or somewhere
    def run_inference(self):
        detection.instance.is_running = not detection.instance.is_running
        print("toggling")

    def refresh(self):
        self.statusPanel.refresh()
        self.controlPanel.refresh()
        self.overlayPanel.refresh()
        self.testPanel.refresh()


def main():
    window.instance = window.Window()
    window.instance.switch_page(MainPage)

    # -------------------------------------------
    while window.instance is not None:
        values.update()
        window.instance.refresh()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()
    # -------------------------------------------


if __name__ == "__main__":
    print("Launching Main Page...")
    main()