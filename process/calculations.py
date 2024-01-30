# Thread for calculating data

import time
import threading
from gui import window
from data import values, rects
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

        # get rect instances
        instances = values.detected_instances
        player: rects.Rect = rects.find_rect_by_class(instances, "Player")
        values.debug_player = player
        
        # get platform
        platform_instances = rects.find_platform_instances(instances)
        if player is not None:
            platform: rects.Rect = rects.find_player_platform(platform_instances, player)
            values.debug_platform = platform

        # get mob
        mob_instances = rects.find_mob_instances(instances)
        if values.debug_platform is not None:
            mob_instances = rects.find_mobs_on_platform(mob_instances, platform)
        if values.debug_player is not None:
            mob: rects.Rect = rects.find_closest_mob(mob_instances, player)
            values.debug_mob = mob

        # get path
        if values.debug_platform is not None:
            path: rects.Rect = rects.find_closest_path(instances, platform)
            values.debug_path = path
        elif values.debug_player is not None:
            path: rects.Rect = rects.find_closest_path(instances, player)  # fallback if no platform is found
            values.debug_path = path

        # # mob logic
        # if values.debug_mob is not None:
        #     values.debug_x_distance = mob.center_x - player.center_x
        #     values.debug_y_distance = player.center_y - mob.center_y
        #     values.debug_direction = keyboard.VK_LEFT if values.debug_x_distance < 0 else keyboard.VK_RIGHT
        #     values.debug_state = "Attack"

        # # platform logic   
        # el
        
        if values.debug_path is not None:
            if player.center_x < path.center_x:  # player is left of platform
                x = path.x1 - player.x2
                # x = path.center_x - player.x2
                values.debug_x_distance = 0 if x < -30 else x  # player is close enough
            else:  # player is right of platform
                x = path.x2 - player.x1
                # x = path.center_x - player.x1
                values.debug_x_distance = 0 if x > 30 else x  # player is close enough

            values.debug_y_distance = player.y2 - path.y1  # inverted, so positive is up, negative is down.
            values.debug_direction = keyboard.VK_LEFT if values.debug_x_distance < 0 else keyboard.VK_RIGHT  # think this is flipped
            values.debug_state = "Navigate"

        # searching logic
        elif values.debug_player is None:
            values.debug_state = "Search"


    def clear_values(self):
        values.debug_player = None
        values.debug_platform = None
        values.debug_mob = None
        values.debug_path = None
        values.debug_x_distance = 0
        values.debug_y_distance = 0
        values.debug_direction = None


instance: CalculationThread = None
