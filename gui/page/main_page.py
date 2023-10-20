#  tkinter main frame
from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.frame import overlay_frame, status_frame, test_frame
from tools import values
from tools import overlay


# Frame layout for main page
class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        self.app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        #
        Label(self, text="Main Page", font='bold').pack(pady=10)
        Button(self, text="Inference", command=lambda: self.run_inference()).pack()
        #
        self.overlayPanel = overlay_frame.OverlayPanel(self)
        self.statusPanel = status_frame.StatusPanel(self)
        self.testPanel = test_frame.TestPanel(self)
        #

    # Need to move this to OverlayPanel or somewhere
    def run_inference(self):
        if overlay.is_visible:
            if values.isWindowActive:
                overlay.instance.run_inferencer() 
            self.after(100, self.run_inference)
        else:
            print("Overlay needs to be visible")


def main():
    window.instance = window.Window()
    window.instance.switch_page(MainPage)

    # -------------------------------------------
    while window.instance is not None:
        values.update()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()
    # -------------------------------------------


if __name__ == "__main__":
    print("Launching Main Page...")
    main()