from tkinter import *
from tkinter import Canvas

import window


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

        self.width = self.instance.winfo_screenwidth()
        self.height = self.instance.winfo_screenheight()

        self.frame.geometry("%dx%d" % (self.width, self.height))
        self.frame.title("Overlay")
        self.frame.attributes('-fullscreen', True)
        self.frame.config(bg='#add123')  # Makes background transparent
        self.frame.wm_attributes('-transparentcolor', '#add123')
        self.frame.wm_attributes("-topmost", True)
        self.frame.wm_attributes("-disabled", True)

        self.canvas = Canvas(self.frame, bg='#add123', bd=0, highlightthickness=0)
        self.canvas.config(width=self.width, height=self.height)  # fill screen

        self.rects = set()
        self.shapes = set()


    def refresh(self):
        for s in self.shapes:
            self.canvas.delete(s)
        self.shapes.clear()

        for s in self.rects:
            rect = self.canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
            self.shapes.add(rect)

        # (x1,y1) top left corner and (x2, y2) bottom right corner
        # self.canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
        # self.canvas.create_rectangle(0, 0, 222, 155, fill='', outline='blue', width=2)
        self.canvas.pack()




def main():
    app = window.Window()
    app.switch_page(OverlayTester)
    app.tk.mainloop()



if __name__ == '__main__':
    main()