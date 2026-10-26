# Thread for calculating data

import time
import threading
from gui import window
from data import config, values, rects
from process import navigation
from tools import movement
from tools import keyboard


class CalculationThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.clear_cache = True
        self.last_target = None  # Mob attacked in the last plan, so the next one doesn't flip between similar mobs
        self.last_mob_seen = 0  # time.time() mobs were last in sight (or the last exploring leg ended)
        self.explore_direction = "up"  # Which way to look for mobs when none are in sight; reversed when there's no way further
        self.explore_from = None  # Map height (feet) the current exploring leg started at


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
        if values.mapper is not None:  # Recorded platforms and ladders, since the detector only finds mobs and loot
            instances = instances + values.mapper.screen_rects()
        player = self.find_player(instances)
        values.debug_player = player

        mapper = values.mapper
        standing = mapper.state == movement.GROUND if mapper is not None and mapper.feet is not None else None
        explore = self.explore(any(r.name == "Mob" for r in instances), player, mapper)
        result = navigation.plan(player, instances, values.nav_jump_height, values.nav_clump_range, self.last_target, explore, standing)
        if explore is not None and result.state is None:  # No way further this way: try the other next time
            self.explore_direction = "down" if explore == "up" else "up"
        self.last_target = result.target if result.state == "Attack" else None  # Kept unless another mob is clearly better
        values.debug_platform = result.platform
        values.debug_state = result.state
        values.debug_route = result.route
        values.debug_x_distance = result.dx
        values.debug_y_distance = result.dy
        values.debug_on_ladder = result.on_ladder
        values.debug_direction = keyboard.VK_LEFT if result.dx < 0 else keyboard.VK_RIGHT
        if result.state == "Attack":
            values.debug_crowd = result.crowd
            values.debug_mob = result.target
        elif result.state == "Navigate":
            values.debug_path = result.target


    def explore(self, mobs_in_sight, player, mapper):  # "up"/"down" once no mobs have been in sight for explore_delay, else None.
        # Each leg ends on reaching another platform, then it waits explore_delay there before going on
        now = time.time()
        if mobs_in_sight or player is None:
            self.last_mob_seen, self.explore_from = now, None
            return None
        if now - self.last_mob_seen < config.explore_delay:
            return None
        feet = mapper.feet if mapper is not None else None
        if feet is not None:
            if self.explore_from is None:
                self.explore_from = feet[1]
            elif abs(feet[1] - self.explore_from) > navigation.feet_margin and mapper.state == movement.GROUND:  # Arrived on another platform
                self.last_mob_seen, self.explore_from = now, None
                return None
        return self.explore_direction


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
