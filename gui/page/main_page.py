# GUI layout for main page

from tkinter import *
from tkinter.ttk import *

from gui import scrolling, window
from gui.panel import application_panel, process_panel, debug_panel, diagnostics_panel, frame_times_panel, stats_panel, utility_panel, test_panel, overlay_panel, bot_panel
from data import config, values

window_width = config.window_width  # Fixed so changing text doesn't resize the window


screen_margin = 80  # Pixels of screen height left free (taskbar, title bar) when the panels are taller than the screen


class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        Frame.__init__(self, app.tk)
        self.canvas, self.scrollbar, self.body = scrolling.scrollable(self)  # Panels scroll when the window is shorter than they are
        #
        body = self.body
        self.applicationPanel = application_panel.ApplicationPanel(body)
        self.utilityPanel = utility_panel.UtilityPanel(body)
        self.controlPanel = process_panel.ProcessPanel(body)
        self.botPanel = bot_panel.BotPanel(body)
        self.statsPanel = stats_panel.StatsPanel(body)
        self.overlayPanel = overlay_panel.OverlayPanel(body)
        self.debugPanel = debug_panel.DebugPanel(body)
        self.diagnosticsPanel = diagnostics_panel.DiagnosticsPanel(body)
        self.frameTimesPanel = frame_times_panel.FrameTimesPanel(body)
        #
        self.update_idletasks()
        height = min(self.body.winfo_reqheight(), self.app.tk.winfo_screenheight() - screen_margin)  # All panels, if the screen fits them
        self.app.tk.geometry("%dx%d" % (window_width + self.scrollbar.winfo_reqwidth(), height))
        self.app.tk.resizable(False, True)  # Taller or shorter as you like; the scrollbar reaches the rest


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