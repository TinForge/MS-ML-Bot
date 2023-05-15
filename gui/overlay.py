#  tkinter overlay frame
from tkinter import *
from tkinter import Canvas
#
import window
from mapletools import tools
#
is_visible = False


class Rect:
    def __init__(self, x1, y1, x2, y2):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


test_rects = [Rect(100, 100, 200, 200), Rect(300, 300, 400, 400), Rect(500, 500, 600, 600)]


class Overlay:


    def __init__(self, instance: Tk):
        self.instance = instance
        self.frame = Toplevel()
        #
        self.width = self.instance.winfo_screenwidth()
        self.height = self.instance.winfo_screenheight()
        #
        self.frame.geometry("%dx%d" % (self.width, self.height))
        self.frame.title("Overlay")
        self.frame.attributes('-fullscreen', True)
        self.frame.config(bg='#add123')  # Makes background transparent
        self.frame.wm_attributes('-transparentcolor', '#add123')
        self.frame.wm_attributes("-topmost", True)
        self.frame.wm_attributes("-disabled", True)
        #
        self.canvas = Canvas(self.frame, bg='#add123', bd=0, highlightthickness=0)
        self.canvas.config(width=self.width, height=self.height)  # fill screen

        # WIP
        self.shapes = set()  # declare data structure

        self.display_rects(test_rects)




    def display_rects(self, new_rects: list):  # rects needs to be a list of rects
        self.rects = new_rects
        # print(self.rects)
        self.clear_shapes()
        self.render_shapes()


    def clear_shapes(self):
        for s in self.shapes:
            self.canvas.delete(s)
        self.shapes.clear()

    def render_shapes(self):
        r: Rect
        for r in self.rects:
            self.shapes.add(self.canvas.create_rectangle(r.x1, r.y1, r.x2, r.y2, fill='', outline='green', width=2))
        self.canvas.pack()



        # (x1,y1) top left corner and (x2, y2) bottom right corner
        # self.canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
        # self.canvas.create_rectangle(0, 0, 222, 155, fill='', outline='blue', width=2)
        # self.canvas.pack()


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

class OverlayTester(Frame):
    def __init__(self, app: window.Window):
        self.instance = app
        Frame.__init__(self, app.tk)
        Button(self, text="Enable Overlay", command=self.new_window).pack()
        Button(self, text="Disable Overlay", command=self.close_window).pack()

    def new_window(self):
        self.overlay = Overlay(self.instance.tk)

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
        self.canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
        self.canvas.create_rectangle(0, 0, 222, 155, fill='', outline='blue', width=2)
        # self.canvas.pack()




def main():
    app = window.Window()
    app.switch_page(OverlayTester)
    app.tk.mainloop()


if __name__ == '__main__':
    main()