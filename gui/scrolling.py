# Scrollable areas: a frame inside a canvas with a vertical scrollbar, scrolled by the mouse wheel over its own window

from tkinter import Canvas, VERTICAL, RIGHT, LEFT, Y, BOTH, NW, Misc
from tkinter.ttk import Frame, Scrollbar


def scrollable(parent):  # Packs a scrollable area into parent; returns (canvas, scrollbar, body), with content going in body
    canvas = Canvas(parent, highlightthickness=0, borderwidth=0)
    scrollbar = Scrollbar(parent, orient=VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    body = Frame(canvas)
    body_window = canvas.create_window((0, 0), window=body, anchor=NW)
    body.bind("<Configure>", lambda event: canvas.configure(scrollregion=canvas.bbox("all")))  # Content grew or shrank
    canvas.bind("<Configure>", lambda event: canvas.itemconfigure(body_window, width=event.width))  # Content fills the width
    parent.winfo_toplevel().scroll_area = (canvas, body)  # Found again from any widget in the window, for the mouse wheel
    canvas.bind_all("<MouseWheel>", on_mouse_wheel)  # One handler for every window: bind_all keeps only the last one bound
    # A dropdown changes its value under the mouse wheel, so scrolling past one (e.g. an attack's key) quietly changed it: scroll instead
    canvas.bind_class("TCombobox", "<MouseWheel>", lambda event: (on_mouse_wheel(event), "break")[1])
    return canvas, scrollbar, body


def on_mouse_wheel(event):  # Scrolls the scrollable area of the window under the mouse, unless it all fits
    if not isinstance(event.widget, Misc):  # Some popups (a combobox's list) report a name, not a widget
        return
    area = getattr(event.widget.winfo_toplevel(), "scroll_area", None)
    if area is None:
        return
    canvas, body = area
    if body.winfo_height() > canvas.winfo_height():
        canvas.yview_scroll(int(-event.delta / 120), "units")
