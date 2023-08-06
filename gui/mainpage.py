#  tkinter main frame
from tkinter import *
from tkinter.ttk import *
import PIL.Image
import PIL.ImageTk
from gui import references, window, overlay
from mapletools import values, tools
from windowtools import savedata


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
        self.overlayPanel = OverlayPanel(self)
        self.statusPanel = StatusPanel(self)
        self.testPanel = TestPanel(self)
        #

    # Need to move this to OverlayPanel or somewhere
    def run_inference(self):
        if overlay.is_visible:
            if values.isWindowActive:
                # overlay.
                self.overlayGraphic.run_inferencer() 
            self.after(100, self.run_inference)
        else:
            print("Overlay needs to be visible")


# Panel layout for Overlay variables
class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)
        #
        self.overlay_visible = Label(self, image=references.red_icon)
        self.overlay_visible.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Is Visible", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        Button(self, text="Toggle Overlay", command=lambda: self.toggle_overlay()).grid(sticky=E, row=1, column=2, padx=0, pady=0)
        #
        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()
        print(overlay.is_visible)


    def toggle_overlay(self):
        overlay.toggle_overlay()
        self.refresh()


    def refresh(self):
        self.overlay_visible.configure(image=(references.red_icon, references.green_icon)[overlay.is_visible])


# Panel layout for Status variables
class StatusPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Status", borderwidth=1, relief=GROOVE)
        #
        self.window_name = Entry(self, textvariable=savedata.window_name.read(), font=references.var_font, width=30)
        self.window_name.grid(row=0, column=0, padx=15, pady=5, columnspan=2)
        self.window_name.bind('<KeyRelease>', self.on_window_name_change)
        self.window_name.insert(0, savedata.window_name.read())
        tools.windowName = self.window_name.get()
        #
        self.window_found = Label(self, image=references.red_icon)
        self.window_found.grid(row=1, column=0, padx=15, pady=5)
        Label(self, text="Window Found", font=references.var_font).grid(sticky=W, row=1, column=1, padx=0, pady=0)
        #
        self.window_active = Label(self, image=references.red_icon)
        self.window_active.grid(row=2, column=0, padx=15, pady=5)
        Label(self, text="Window Active", font=references.var_font).grid(sticky=W, row=2, column=1, padx=0, pady=0)
        #
        self.grid_columnconfigure(1, weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()

    def refresh(self):
        self.window_found.configure(image=(references.red_icon, references.green_icon)[values.isWindowFound])
        self.window_active.configure(image=(references.red_icon, references.green_icon)[values.isWindowActive])
        self.after(500, self.refresh)

    def on_window_name_change(self, event):
        savedata.window_name.save(self.window_name.get())
        tools.windowName = self.window_name.get()


# Panel layout for Test variables
class TestPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Test", borderwidth=1, relief=GROOVE)
        #
        Button(self, text="Show Window", command=lambda: self.show_window()).grid(sticky=W, row=0, column=0, padx=10, pady=5)
        #
        Label(self, text="Rect").grid(sticky=W, row=1, column=0, padx=10, pady=5)
        self.window_rect_display = Label(self)
        self.window_rect_display.grid(row=1, column=1, padx=10, pady=5)
        #
        self.grid_columnconfigure((0, 1), weight=1, uniform="column")
        self.pack(fill=X)
        self.refresh()
        #

    def show_window(self):
        tools.set_window_rect()

    def refresh(self):
        self.window_rect_display['text'] = str(values.windowRect)
        self.after(500, self.refresh)



def main():
    window.instance = window.Window()
    window.instance.switch_page(MainPage)
    window.instance.tk.protocol("WM_DELETE_WINDOW", on_closing)
    references.initialize_images()

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