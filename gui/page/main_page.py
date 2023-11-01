# GUI layout for main page

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.panel import application_panel, process_panel, debug_panel, utility_panel, test_panel, overlay_panel
from data import values


class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        self.app.tk.geometry("300x550")
        Frame.__init__(self, app.tk)
        #
        self.applicationPanel = application_panel.ApplicationPanel(self)
        self.utilityPanel = utility_panel.UtilityPanel(self)
        self.controlPanel = process_panel.ProcessPanel(self)
        self.overlayPanel = overlay_panel.OverlayPanel(self)
        self.debugPanel = debug_panel.DebugPanel(self)


    def refresh(self):
        self.applicationPanel.refresh()
        self.utilityPanel.refresh()
        self.controlPanel.refresh()
        self.overlayPanel.refresh()
        self.debugPanel.refresh()


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