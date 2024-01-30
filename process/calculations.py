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

        # mob logic
        if values.debug_mob is not None:
            values.debug_x_distance = mob.center_x - player.center_x
            values.debug_y_distance = player.center_y - mob.center_y
            values.debug_direction = keyboard.VK_LEFT if values.debug_x_distance < 0 else keyboard.VK_RIGHT
            values.debug_state = "Attack"

        # platform logic   
        elif values.debug_platform is not None:
            if player.center_x < platform.x1:
                values.debug_x_distance = platform.x1 - player.center_x
            else:
                values.debug_x_distance = platform.x2 - player.center_x
            values.debug_y_distance = player.center_y - platform.center_y
            values.debug_direction = keyboard.VK_LEFT if values.debug_x_distance < 0 else keyboard.VK_RIGHT
            values.debug_state = "Platform"



    def clear_values(self):
        values.debug_player = None
        values.debug_platform = None
        values.debug_mob = None
        values.debug_x_distance = 0
        values.debug_y_distance = 0
        values.debug_direction = None


instance: CalculationThread = None
