#  Renders overlay rects of captured classifications

from tkinter import *
from tkinter import Canvas
from gui import window
from yolov5 import detection


# Data container for rect bounds
class Rect:
    def __init__(self, x1, y1, x2, y2, color):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color


# Test set of rects
test_rects = [Rect(100, 100, 200, 200, "green"), Rect(300, 300, 400, 400, "red"), Rect(500, 500, 600, 600, "purple")]


# --------------------------------------------


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
        #
        self.shapes = set()  # declare data structure
        #
        self.display_rects(test_rects)
        #
        self.model = detection.Model()

    def display_rects(self, new_rects: list):
        self.rects = new_rects
        self.clear_shapes()
        self.render_shapes()

    def clear_shapes(self):
        for s in self.shapes:
            self.canvas.delete(s)
        self.shapes.clear()

    def render_shapes(self):
        r: Rect
        for r in self.rects:
            self.shapes.add(self.canvas.create_rectangle(r.x1, r.y1, r.x2, r.y2, fill='', outline=r.color, width=4))
        self.canvas.pack()

    def run_inferencer(self):
        print("RUNNING INFERENCER")
        rects = self.model.run()
        self.display_rects(rects)


class OverlayTester(Frame):
    def __init__(self, app: window.Window):
        self.instance = app
        Frame.__init__(self, app.tk)
        Button(self, text="Enable Overlay", command=enable_overlay).pack()
        Button(self, text="Disable Overlay", command=disable_overlay).pack()


def enable_overlay():
    global instance, is_visible
    instance = Overlay(window.instance.tk)
    is_visible = True


def disable_overlay():    
    global instance, is_visible
    instance.frame.destroy()
    is_visible = False


def toggle_overlay():
    global is_visible
    if is_visible:
        disable_overlay()
    else:
        enable_overlay()


def main():
    window.instance = window.Window()
    window.instance.switch_page(OverlayTester)
    window.instance.tk.mainloop()


if __name__ == '__main__':
    main()

instance: Overlay = None
is_visible = False