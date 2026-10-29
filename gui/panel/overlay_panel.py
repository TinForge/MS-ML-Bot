# GUI Section for Debug

from tkinter import *
from tkinter.ttk import *

from gui import references
from gui.widgets import update
from data import values
from process import bot
from tools import overlay


OPTIONS = ["Monsters", "Platforms", "Route", "Attack Range", "Targets", "Player", "Window", "Minimap"]
FLAGS = {  # Options that switch a values flag rather than just drawing
    "Window": "show_window_rect",  # The detected game area
    "Player": "show_player_rect",  # The player found by their nametag
    "Minimap": "show_minimap",  # The minimap's map area and the player's dot
    "Platforms": "show_platforms",  # Recorded platforms, ladders and the player's feet
    "Attack Range": "show_attack_range",  # The bot profile's attack ranges around the player
}


class OverlayPanel(LabelFrame):
    def __init__(self, frame):
        LabelFrame.__init__(self, frame, text="Overlay", borderwidth=1, relief=GROOVE)

        self.overlay_visible = Label(self, image=references.red_icon)
        self.overlay_visible.grid(row=1, column=0, padx=15, pady=5)
        Button(self, text="Toggle", command=lambda: self.toggle_overlay()).grid(sticky=E, row=1, column=2, padx=0, pady=0)

        self.selected_options = []
        self.listbox = Listbox(self, selectmode=MULTIPLE, height=len(OPTIONS), exportselection=False)
        for option in OPTIONS:
            self.listbox.insert(END, option)
        self.listbox.bind("<<ListboxSelect>>", lambda event: self.on_selection())

        self.listbox.grid(row=1, column=1, pady=5, sticky="ew")  # ew expands east-west

        self.grid_columnconfigure(2, weight=1, uniform="column")
        self.pack(fill=X)


    def on_selection(self):  # Picked options are drawn; picking one also shows the overlay
        picked = [OPTIONS[i] for i in self.listbox.curselection()]
        if any(option not in self.selected_options for option in picked) and not overlay.is_visible:
            overlay.enable_overlay()
        self.selected_options = picked
        for option, flag in FLAGS.items():  # These also turn on the work behind them, e.g. searching for the player
            setattr(values, flag, option in picked)

    def toggle_overlay(self):
        overlay.toggle_overlay()


    def refresh(self):
        update(self.overlay_visible, image=(references.red_icon, references.green_icon)[overlay.is_visible])

        if overlay.instance is not None:
            overlay.instance.clear_shapes()

            if values.show_window_rect and values.window_rect is not None:
                overlay.instance.render_window(values.window_rect)

            if values.show_player_rect and values.player_rect is not None:
                overlay.instance.render_player(values.player_rect)

            if values.show_minimap and values.minimap is not None:
                overlay.instance.render_minimap(values.minimap)

            profile = bot.instance.profile if bot.instance is not None else None
            if values.show_attack_range and values.player_rect is not None and profile is not None:
                overlay.instance.render_attack_ranges(values.player_rect, profile.attacks)

            if values.show_platforms and values.mapper is not None and values.window_rect is not None:
                overlay.instance.render_platforms(values.mapper, values.window_rect, values.erase_platforms)

            route = values.planned_route  # Read once: the calculations thread replaces it every frame
            if "Route" in self.selected_options and route and values.mapper is not None and values.window_rect is not None:
                overlay.instance.render_route(values.mapper, values.window_rect, route)

            if values.detected_instances is not None:

                if "Monsters" in self.selected_options:  # The detector's boxes, with confidence
                    overlay.instance.render_box(values.detected_instances)

                if "Targets" in self.selected_options:
                    if values.debug_player is not None:
                        d = values.debug_player
                        overlay.instance.render_floor([d])
                    if values.debug_mob is not None:
                        d = values.debug_mob                        
                        overlay.instance.render_circle([d])
                    if values.debug_path is not None:
                        d = values.debug_path                        
                        overlay.instance.render_floor([d])
