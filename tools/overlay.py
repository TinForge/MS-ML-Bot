#  Renders overlay rects of captured classifications

from tkinter import *
from tkinter import Canvas
import ctypes
from gui import window
from data import rects

WDA_EXCLUDEFROMCAPTURE = 0x11  # Keeps the overlay out of screen captures, so detection never sees its own drawings


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
        self.frame.update_idletasks()  # Creates the window handle
        ctypes.windll.user32.SetWindowDisplayAffinity(ctypes.windll.user32.GetParent(self.frame.winfo_id()), WDA_EXCLUDEFROMCAPTURE)
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
            text = str(r.confidence) + (" %d%%" % round(r.health * 100) if getattr(r, "health", None) is not None else "")
            self.shapes.add(self.canvas.create_text((r.x1 + r.x2) / 2, r.y1 - 6, text=text, font=("Arial", 12)))
            #  canvas.create_text(x, y, text=texto, font=("Arial", 12), fill="black")
        self.canvas.pack()

    def render_window(self, window_rect, color='lime', thickness=2):
        x1, y1, x2, y2 = window_rect
        self.shapes.add(self.canvas.create_rectangle(x1, y1, x2 - 1, y2 - 1, fill='', outline=color, width=thickness))
        self.shapes.add(self.canvas.create_text(x1 + 6, y1 + 6, anchor=NW, text="%dx%d @ (%d, %d)" % (x2 - x1, y2 - y1, x1, y1), fill=color, font=("Arial", 12)))
        self.canvas.pack()

    def render_player(self, player_rect, color='cyan', thickness=2):
        x1, y1, x2, y2 = player_rect
        self.shapes.add(self.canvas.create_rectangle(x1, y1, x2, y2, fill='', outline=color, width=thickness))
        self.canvas.pack()

    def render_minimap(self, minimap, color='magenta', thickness=2):  # Map area outline and a ring around the player's dot
        x1, y1, x2, y2 = minimap.map_rect
        self.shapes.add(self.canvas.create_rectangle(x1 - 1, y1 - 1, x2, y2, fill='', outline=color, width=thickness))
        if minimap.player is not None:
            px, py = x1 + minimap.player[0], y1 + minimap.player[1]
            self.shapes.add(self.canvas.create_oval(px - 8, py - 8, px + 8, py + 8, fill='', outline='cyan', width=thickness))
        self.canvas.pack()

    def render_platforms(self, mapper, frame_rect):  # Recorded platforms coloured by how safe from mobs they are, ladders (always
        # safe: mobs don't climb) and the player's feet, from map coords. Orange: not watched long enough to tell yet
        colors = {"safe": "#30e040", "occasional": "yellow", "busy": "red", "unknown": "orange"}
        for safety, line in mapper.safety or [("unknown", line) for line in mapper.lines]:
            points = [mapper.to_screen(p, frame_rect) for p in line]
            if None not in points and len(points) >= 2:
                self.shapes.add(self.canvas.create_line(*[c for p in points for c in p], fill=colors[safety], width=3))
        for ladder in mapper.ladders:
            top, bottom = mapper.to_screen((ladder["x"], ladder["top"]), frame_rect), mapper.to_screen((ladder["x"], ladder["bottom"]), frame_rect)
            if top is not None and bottom is not None:
                self.shapes.add(self.canvas.create_line(*top, *bottom, fill=colors["safe"], width=3, dash=(6, 2)))
        feet = mapper.feet
        point = mapper.to_screen(feet, frame_rect) if feet is not None else None
        if point is not None:
            x, y = point
            self.shapes.add(self.canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill='red', outline='white'))
        self.canvas.pack()

    def render_attack_ranges(self, player_rect, attacks):  # Each attack's reach around the player, on both sides. Solid: where a mob's
        # nearer edge must be (and its centre's height) for the bot to use it (range_x, range_y); dotted: the extra height a jump attack
        # reaches; dashed: how far a mobbing attack hits (hit_range, to mobs' nearer edges)
        colors = ("#ff4040", "#ffb000", "#40c0ff", "#c060ff", "#40ff80")
        x1, y1, x2, y2 = player_rect
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        for i, attack in enumerate(attacks):
            color = colors[i % len(colors)]
            top, bottom = cy - attack.range_y[1], cy - attack.range_y[0]  # range_y is height above the player's centre
            for side in (1, -1):
                near, far = cx + side * attack.range_x[0], cx + side * attack.range_x[1]
                self.shapes.add(self.canvas.create_rectangle(min(near, far), top, max(near, far), bottom, outline=color, width=2))
                if attack.jump_attack:
                    self.shapes.add(self.canvas.create_rectangle(min(near, far), top - attack.jump_reach, max(near, far), top, outline=color, width=1, dash=(1, 3)))
                if attack.min_mobs > 1:
                    reach = cx + side * attack.reach
                    self.shapes.add(self.canvas.create_rectangle(min(cx, reach), top - 3, max(cx, reach), bottom + 3, outline=color, width=1, dash=(6, 3)))
            self.shapes.add(self.canvas.create_text(cx + attack.range_x[1] + 4, top + 14 * i, anchor=NW, text=attack.name, fill=color, font=("Arial", 10)))
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