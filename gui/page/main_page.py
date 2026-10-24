# GUI layout for main page

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.panel import application_panel, process_panel, debug_panel, diagnostics_panel, frame_times_panel, stats_panel, utility_panel, test_panel, overlay_panel, bot_panel
from data import values

window_width = 390  # Fixed so changing text doesn't resize the window


class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        Frame.__init__(self, app.tk)
        #
        self.applicationPanel = application_panel.ApplicationPanel(self)
        self.utilityPanel = utility_panel.UtilityPanel(self)
        self.controlPanel = process_panel.ProcessPanel(self)
        self.botPanel = bot_panel.BotPanel(self)
        self.statsPanel = stats_panel.StatsPanel(self)
        self.overlayPanel = overlay_panel.OverlayPanel(self)
        self.debugPanel = debug_panel.DebugPanel(self)
        self.diagnosticsPanel = diagnostics_panel.DiagnosticsPanel(self)
        self.frameTimesPanel = frame_times_panel.FrameTimesPanel(self)
        #
        self.update_idletasks()
        self.app.tk.geometry("%dx%d" % (window_width, self.winfo_reqheight()))  # Height fits the panels once, at startup


    def refresh(self):
        self.applicationPanel.refresh()
        self.utilityPanel.refresh()
        self.controlPanel.refresh()
        self.botPanel.refresh()
        self.statsPanel.refresh()
        self.overlayPanel.refresh()
        self.debugPanel.refresh()
        self.diagnosticsPanel.refresh()
        self.frameTimesPanel.refresh()


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