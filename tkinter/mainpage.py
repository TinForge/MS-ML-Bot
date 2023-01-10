from tkinter import *
from tkinter.ttk import *
import PIL.Image
import PIL.ImageTk
import window
import startpage
import references

overlay_active = False


class MainPage(Frame):
    def __init__(self, app: window.Window):
        app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        Label(self, text="Main Page", font='bold').pack(pady=10)
        Button(self, text="Toggle Overlay", command=lambda: self.toggle_overlay()).pack()
        OverlayPanel(self)
        StatusPanel(self)

    def toggle_overlay(self):
        global overlay_active
        overlay_active = not overlay_active
        print("Toggled Overlay to " + str(overlay_active))
        window.instance.switch_page(MainPage)


class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        global overlay_active
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)
        Label(self, text="Overlay Display:").grid(row=1, column=0, padx=10, pady=10)
        Label(self, text=overlay_active).grid(row=1, column=1, padx=10, pady=10)
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)


class StatusPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Status", borderwidth=1, relief=GROOVE)
        Label(self, text="Maplestory Found:").grid(row=0, column=0, padx=10, pady=10)
        Label(self, text="No").grid(row=0, column=1, padx=10, pady=10)
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)


def main():
    window.instance = window.Window()
    window.instance.switch_page(MainPage)
    window.instance.tk.mainloop()


if __name__ == "__main__":
    print("Launching Main Page...")
    main()