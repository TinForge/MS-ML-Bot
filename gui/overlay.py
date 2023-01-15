from tkinter import *
from tkinter import Canvas

import window
from detection import detect


class OverlayTester(Frame):
    def __init__(self, app: window.Window):
        self.instance = app
        Frame.__init__(self, app.tk)
        Button(self, text="Enable Overlay", command=self.new_window).pack()
        Button(self, text="Disable Overlay", command=self.close_window).pack()

    def new_window(self):
        self.overlay = Overlay(self.instance.tk)

    def close_window(self):
        self.overlay.frame.destroy()


class Overlay:
    def __init__(self, instance: Tk):
        self.instance = instance
        self.frame = Toplevel()

        width = self.instance.winfo_screenwidth()
        height = self.instance.winfo_screenheight()

        self.frame.geometry("%dx%d" % (width, height))
        self.frame.title("Overlay")
        self.frame.attributes('-fullscreen', True)
        self.frame.config(bg='#add123')  # Makes background transparent
        self.frame.wm_attributes('-transparentcolor', '#add123')
        self.frame.wm_attributes("-topmost", True)
        self.frame.wm_attributes("-disabled", True)


        canvas = Canvas(self.frame, bg='#add123', bd=0, highlightthickness=0)
        canvas.config(width=width, height=height)  # fill screen
        # (x1,y1) top left corner and (x2, y2) bottom right corner
        canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
        canvas.create_rectangle(0, 0, 222, 155, fill='', outline='blue', width=2)
        canvas.pack()



def main():
    app = window.Window()
    app.switch_page(OverlayTester)
    app.tk.mainloop()



if __name__ == '__main__':
    main()