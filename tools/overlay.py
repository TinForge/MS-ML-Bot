#  Renders overlay rects of captured classifications

from tkinter import *
from tkinter import Canvas
from gui import window
from data import rects


class Overlay:
    def __init__(self, instance: Tk):
        self.tk = instance
        self.frame = Toplevel()
        #
        self.width = self.tk.winfo_screenwidth()
        self.height = self.tk.winfo_screenheight()
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
        # self.display_rects(rects.test_rects)  # Display default


    def display_rects(self, new_rects: list):
        self.rects = new_rects
        self.clear_shapes()
        self.render_box()


    def clear_shapes(self):
        for s in self.shapes:
            self.canvas.delete(s)
        self.shapes.clear()

    def render_box(self, new_rects: list, thickness=1):
        r: rects.Rect
        for r in new_rects:
            self.shapes.add(self.canvas.create_rectangle(r.x1, r.y1, r.x2, r.y2, fill='', outline=r.color, width=thickness))
            self.shapes.add(self.canvas.create_text((r.x1 + r.x2) / 2, r.y1 - 6, text=str(r.confidence), font=("Arial", 12)))
            #  canvas.create_text(x, y, text=texto, font=("Arial", 12), fill="black")
        self.canvas.pack()

    def render_circle(self, new_rects: list, offset=6):
        r: rects.Rect
        for r in new_rects:
            self.shapes.add(self.canvas.create_oval(r.center_x - offset, r.y1 - offset, r.center_x + offset, r.y1 + offset, fill=r.color, outline=r.color, width=1))


    def render_floor(self, new_rects: list, thickness=5, offset=10):
        r: rects.Rect
        for r in new_rects:
            self.shapes.add(self.canvas.create_line(r.x1, r.y2 + offset, r.x2, r.y2 + offset, fill=r.color, width=thickness))


def toggle_overlay():
    global is_visible
    if is_visible:
        disable_overlay()
    else:
        enable_overlay()


def enable_overlay():
    global instance, is_visible
    instance = Overlay(window.instance.tk)
    is_visible = True


def disable_overlay():    
    global instance, is_visible
    instance.frame.destroy()
    instance = None
    is_visible = False


# ----------------------------------------------

# class OverlayTester(Frame):
#     def __init__(self, app: window.Window):
#         Frame.__init__(self, app.tk)
#         Button(self, text="Enable Overlay", command=enable_overlay).pack()
#         Button(self, text="Disable Overlay", command=disable_overlay).pack()


# def main():
#     window.instance = window.Window()
#     window.instance.switch_page(OverlayTester)
#     window.instance.tk.mainloop()


# if __name__ == '__main__':
#     main()

instance: Overlay = None
is_visible = False