from tkinter import *
from tkinter.ttk import *
import PIL.Image
import PIL.ImageTk
import window
import overlay

overlay_visible = False
maplestory_found = False



class MainPage(Frame):
    def __init__(self, app: window.Window):
        self.app = app
        self.app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        Label(self, text="Main Page", font='bold').pack(pady=10)
        Button(self, text="Toggle Overlay", command=lambda: self.toggle_overlay()).pack()
        self.overlayPanel = OverlayPanel(self)
        self.statusPanel = StatusPanel(self)
        self.overlay1 = None

    def toggle_overlay(self):
        global overlay_visible
        overlay_visible = not overlay_visible
        if overlay_visible:
            self.overlay1 = overlay.Overlay(self.app.tk)
        else:
            self.overlay1.frame.destroy()

        self.overlayPanel.refresh()
        self.statusPanel.refresh()


class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)
        Label(self, text="Overlay Visible:").grid(row=1, column=0, padx=10, pady=10)
        self.overlay_visible_text = Label(self)
        self.overlay_visible_text.grid(row=1, column=1, padx=10, pady=10)
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()

    def refresh(self):
        global overlay_visible
        self.overlay_visible_text['text'] = overlay_visible


class StatusPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Status", borderwidth=1, relief=GROOVE)
        Label(self, text="Maplestory Found:").grid(row=0, column=0, padx=10, pady=10)
        self.maplestory_found_text = Label(self)
        self.maplestory_found_text.grid(row=0, column=1, padx=10, pady=10)
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()

    def refresh(self):
        global maplestory_found
        self.maplestory_found_text['text'] = maplestory_found


def main():
    window.instance = window.Window()
    window.instance.switch_page(MainPage)
    window.instance.tk.mainloop()


if __name__ == "__main__":
    print("Launching Main Page...")
    main()