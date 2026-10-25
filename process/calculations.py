# Thread for calculating data

import time
import threading
from gui import window
from data import values, rects
from process import navigation
from tools import keyboard


class CalculationThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.clear_cache = True


    def run(self):
        while window.instance is not None:
            if self.clear_cache:  # if false, the last valid values will be used, which might be more suitable for bot logic
                self.clear_values()

            if self.is_running is False:
                time.sleep(0.1)  # Adjustable
            else:
                self.calculate()
                time.sleep(0.01)  # Adjustable


    def calculate(self):
        if values.detected_instances is None:  # Return if no data to work with
            return

        instances = values.detected_instances
        player = self.find_player(instances)
        values.debug_player = player

        result = navigation.plan(player, instances, values.nav_jump_height)
        values.debug_platform = result.platform
        values.debug_state = result.state
        values.debug_route = result.route
        values.debug_x_distance = result.dx
        values.debug_y_distance = result.dy
        values.debug_on_ladder = result.on_ladder
        values.debug_direction = keyboard.VK_LEFT if result.dx < 0 else keyboard.VK_RIGHT
        if result.state == "Attack":
            values.debug_mob = result.target
        elif result.state == "Navigate":
            values.debug_path = result.target


    def find_player(self, instances):  # The player found by their nametag, or YOLO's Player box if the nametag isn't visible
        if values.player_rect is not None:
            x1, y1, x2, y2 = values.player_rect
            return rects.Rect("Player", "blue", x1, y1, x2, y2, 1)
        return rects.find_rect_by_class(instances, "Player")


    def clear_values(self):
        values.debug_player = None
        values.debug_platform = None
        values.debug_mob = None
        values.debug_path = None
        values.debug_route = None
        values.debug_on_ladder = False
        values.debug_x_distance = 0
        values.debug_y_distance = 0
        values.debug_direction = None


instance: CalculationThread = None
