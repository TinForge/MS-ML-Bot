from tkinter import *
from tkinter.ttk import *
#
import PIL.Image
import PIL.ImageTk
#
import window
import overlay
#
from mapletools import values,tools


# Frame layout for main page
class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        self.app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        #
        Label(self, text="Main Page", font='bold').pack(pady=10)
        Button(self, text="Toggle Overlay", command=lambda: self.toggle_overlay()).pack()
        #
        self.overlayGraphic = None
        self.overlayPanel = OverlayPanel(self)
        self.statusPanel = StatusPanel(self)
        self.testPanel = TestPanel(self)

    def toggle_overlay(self):
        overlay.is_visible = not overlay.is_visible
        if overlay.is_visible:
            self.overlayGraphic = overlay.Overlay(self.app.tk)
        else:
            self.overlayGraphic.frame.destroy()

        self.overlayPanel.refresh()


# Panel layout for Overlay variables
class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)
        #
        Label(self, text="Is Visible").grid(sticky=W, row=1, column=0, padx=10, pady=10)
        #
        self.overlay_visible_text = Label(self)
        self.overlay_visible_text.grid(row=1, column=1, padx=10, pady=10)
        #
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()

    def refresh(self):
        self.overlay_visible_text['text'] = str(overlay.is_visible)


# Panel layout for Status variables
class StatusPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Status", borderwidth=1, relief=GROOVE)
        #
        Label(self, text="Window Found").grid(sticky=W, row=0, column=0, padx=10, pady=5)
        self.window_found_display = Label(self)
        self.window_found_display.grid(row=0, column=1, padx=10, pady=5)
        #
        Label(self, text="Window Visible").grid(sticky=W, row=1, column=0, padx=10, pady=5)
        self.window_visible_display = Label(self)
        self.window_visible_display.grid(row=1, column=1, padx=10, pady=5)
        #
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()

    def refresh(self):
        self.window_found_display['text'] = str(values.isWindowFound)
        self.window_visible_display['text'] = str(values.isWindowEnabled)
        self.after(500, self.refresh)


# Panel layout for Test variables
class TestPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Test", borderwidth=1, relief=GROOVE)
        #
        Button(self, text="TEST", command=lambda: self.TEST()).grid(sticky=W, row=0, column=0, padx=10, pady=5)
        #
        Label(self, text="Rect").grid(sticky=W, row=1, column=0, padx=10, pady=5)
        self.window_rect_display = Label(self)
        self.window_rect_display.grid(row=1, column=1, padx=10, pady=5)
        #
        self.grid_columnconfigure((0), weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()
        #

    def TEST(self):
        tools.ShowWindow()


    def refresh(self):
        self.window_rect_display['text'] = str(values.windowRect)
        self.after(500, self.refresh)





def main():
    window.instance = window.Window()
    window.instance.switch_page(MainPage)
    window.instance.tk.protocol("WM_DELETE_WINDOW", on_closing)

    # -------------------------------------------
    while window.instance is not None:
        values.update()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()

    # -------------------------------------------


def on_closing():
    print("Closing window")
    window.instance.tk.destroy()
    window.instance = None


if __name__ == "__main__":
    print("Launching Main Page...")
    main()