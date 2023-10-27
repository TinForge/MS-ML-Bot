# GUI layout for main page

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.panel import process_panel, status_panel, debug_panel, utility_panel, test_panel
from data import values


class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        self.app.tk.geometry("300x500")
        Frame.__init__(self, app.tk)
        #
        # Label(self, text="Main Page", font='bold').pack(pady=10)
        # Button(self, text="Inference", command=lambda: self.run_inference()).pack()
        #
        self.statusPanel = status_panel.StatusPanel(self)
        self.controlPanel = process_panel.ProcessPanel(self)
        self.debugPanel = debug_panel.DebugPanel(self)
        self.utilityPanel = utility_panel.UtilityPanel(self)


    def refresh(self):
        self.statusPanel.refresh()
        self.controlPanel.refresh()
        self.debugPanel.refresh()
        self.utilityPanel.refresh()


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