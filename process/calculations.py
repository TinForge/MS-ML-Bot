# Thread for calculating data

import time
import threading
from gui import window
from data import config, values, rects
from process import kills, navigation
from tools import map_recorder, movement
from tools.route_planner import RoutePlanner
from tools import keyboard


climb_progress = 5  # Map pixels a climb must rise to count as getting somewhere
climb_stuck_time = 1.2  # Seconds climbing without rising before jumping off
climb_max_time = 6.0  # Longest climb when its progress can't be measured (map position unknown)
top_hold = 0.4  # Seconds Up stays held after a climb seems over: at a rope's top the platform overlaps it, so ground shows under
# the feet a moment before the character has stepped off
explore_min_width = 150  # Narrowest platform worth exploring to: single stair steps and scraps of recording aren't
jump_give_up = 3.0  # Seconds trying to jump up onto the same platform before taking it for out of reach
jump_phase = 60  # Within this distance of a platform's edge the bot is jumping for it, not walking to it
unreachable_time = 15.0  # Seconds a platform that couldn't be jumped onto is left out of the routes up (a rope is used instead)


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
        self.climb_since = None  # When the current climb started, and the highest point and when it was reached, to spot a stuck one
        self.climb_best = None
        self.climb_progress = None
        self.climb_until = 0  # time.time() until which a climb that seems over carries on, for top_hold
        self.jump_key, self.jump_since = None, None  # The platform being jumped for (see platform_key), and since when
        self.unreachable = {}  # platform_key: time.time() until which it isn't jumped for
        self.planner, self.planner_key = None, None  # Route planner for the recorded map, rebuilt when the recording changes
        self.explore_goal = None  # Platform (index in the recording) being headed for while exploring


    def run(self):
        planned_for = None  # The detections and stats reading the last plan used
        while window.instance is not None:
            if self.is_running is False:
                if self.clear_cache:
                    self.clear_values()
                planned_for = None
                time.sleep(0.1)
                continue
            inputs = (id(values.detected_instances), values.player_read_id)  # A new detection frame, or a new player position and map reading
            if inputs == planned_for:  # Nothing new to plan from: planning again would repeat the last plan
                time.sleep(0.002)
                continue
            planned_for = inputs
            if self.clear_cache:  # if false, the last valid values will be used, which might be more suitable for bot logic
                self.clear_values()
            self.calculate()


    def calculate(self):
        if values.detected_instances is None:  # Return if no data to work with
            return

        instances = values.detected_instances
        if values.exp_check_active:  # Killed mobs fading out aren't targets
            instances = kills.instance.alive(instances, time.time())
        if values.mapper is not None:  # Recorded platforms and ladders, since the detector only finds mobs and loot
            instances = instances + values.mapper.screen_rects()
        player = self.find_player(instances)
        values.debug_player = player

        mapper = values.mapper
        state = mapper.state if mapper is not None and player is not None else None  # Ground / Ladder / Air, from how the player moves
        values.player_speed = mapper.movement.vx if state is not None else None
        standing = None if state is None else state == movement.GROUND
        explore = self.explore(any(r.name == "Mob" for r in instances), player, mapper)
        skip = self.unreachable_platforms(instances, mapper)
        values.planned_route = None  # Set again below if this frame's plan follows a route
        router = lambda goal: self.route_step(goal, mapper)
        result = navigation.plan(player, instances, values.nav_jump_height, values.nav_clump_range, self.last_target, explore, standing,
                                 state == movement.LADDER, skip, router)
        result = self.unstick_climb(result, player, mapper)
        result = self.finish_climb(result)
        self.watch_jumps(result, mapper)
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


    def route_planner(self, mapper):  # For the recorded map; None without one
        if mapper is None or not mapper.lines:
            return None
        key = (id(mapper.lines), id(mapper.ladders), values.nav_jump_height)  # The mapper publishes new lists when the recording changes
        if key != self.planner_key:
            self.planner, self.planner_key = RoutePlanner(mapper.lines, mapper.ladders, values.nav_jump_height), key
            self.explore_goal = None
        return self.planner

    def route_step(self, goal, mapper):  # The first step of the quickest route to the goal mob's platform (goal None: to a platform
        # worth exploring), as a navigation.Step in screen coords; None without a recorded way there
        planner = self.route_planner(mapper)
        shift = mapper.screen_shift(mapper.frame_rect) if planner is not None else None
        feet = mapper.feet if planner is not None else None
        if shift is None or feet is None:
            return None
        start = planner.line_at(*feet)
        if start is None:  # In the air or on a rope: the local moves handle those
            return None
        dx, dy = shift
        avoid = self.unreachable_lines(mapper, shift) if self.unreachable else set()
        if goal is not None:
            end = planner.line_at(goal.center_x - dx, goal.y2 - dy)
            if end is None or planner.same_platform(start, end):  # The same platform, maybe recorded in pieces: just walk
                return None
            hops = planner.route(start, feet[0], end, avoid)
        else:
            hops = self.explore_route(planner, mapper, start, feet[0], avoid)
        if not hops:
            return None
        values.planned_route = planner.path(start, feet[0], hops)  # For the overlay's Route option
        hop = hops[0]
        if hop.kind == "rope":
            ladder = mapper.ladders[hop.ladder]
            x = ladder["x"] + dx
            target = rects.Rect("Ladder", "yellow", x - map_recorder.ladder_width / 2, ladder["top"] + dy, x + map_recorder.ladder_width / 2,
                                ladder["bottom"] + dy, 1)
        else:
            target = rects.PlatformLine([(x + dx, y + dy) for x, y in mapper.lines[hop.to]])
        return navigation.Step(hop.kind, target, hop.x1 + dx, hop.x2 + dx)

    def explore_route(self, planner, mapper, start, x, avoid):  # Toward the nearest platform where mobs have been seen; failing
        # that, the nearest one not watched long enough to know. The goal is kept until it's reached, so the route doesn't waver
        reachable = planner.routes(start, x, avoid)
        if self.explore_goal is None or planner.same_platform(self.explore_goal, start) or self.explore_goal not in reachable:
            busy, unknown = [], []
            for line, (seconds, _) in reachable.items():
                if planner.same_platform(line, start) or planner.width(line) < explore_min_width:  # Not here, nor a tiny step or scrap
                    continue
                mobs, watched = mapper.platforms.activity(mapper.lines[line])
                if watched >= map_recorder.learn_time and mobs / watched >= map_recorder.safe_share:
                    busy.append((seconds, line))
                elif watched < map_recorder.learn_time:
                    unknown.append((seconds, line))
            choices = busy or unknown
            self.explore_goal = min(choices)[1] if choices else None
        return reachable[self.explore_goal][1] if self.explore_goal is not None else None

    def unreachable_lines(self, mapper, shift):  # Recorded platforms whose jumps kept failing
        dx, dy = shift
        lines = [rects.PlatformLine([(x + dx, y + dy) for x, y in line]) for line in mapper.lines]
        return {i for i, line in enumerate(lines) if self.platform_key(line, mapper) in self.unreachable}

    def platform_key(self, rect, mapper):  # Names a platform the same from frame to frame: map coords when known (the camera moves),
        # rounded so small jitter doesn't change it
        shift = mapper.screen_shift(mapper.frame_rect) if mapper is not None else None
        dx, dy = shift if shift is not None else (0, 0)
        return round((rect.x1 - dx) / 20), round((rect.y1 - dy) / 10)

    def unreachable_platforms(self, instances, mapper):  # Platforms left out of the routes up for now
        now = time.time()
        self.unreachable = {key: until for key, until in self.unreachable.items() if until > now}
        if not self.unreachable:
            return []
        return [r for r in instances if r.name == "Platform" and self.platform_key(r, mapper) in self.unreachable]

    def watch_jumps(self, result, mapper):  # Trying to jump up onto the same platform for too long: it's out of reach after all
        target = result.target
        if result.route != "up" or target is None or target.name != "Platform" or abs(result.dx) > jump_phase:
            self.jump_key = None  # Not jumping for a platform (still walking to it doesn't count)
            return
        now, key = time.time(), self.platform_key(target, mapper)
        if key != self.jump_key:
            self.jump_key, self.jump_since = key, now
        elif now - self.jump_since > jump_give_up:
            self.unreachable[key] = now + unreachable_time
            self.jump_key = None

    def finish_climb(self, result):  # Keeps climbing a little after the plan stops, so it steps off at the top instead of hanging there
        now = time.time()
        if result.route == "climb":
            self.climb_until = now + top_hold
        elif result.route == "jump_off":
            self.climb_until = 0  # Leaving the rope on purpose
        elif now < self.climb_until:
            return navigation.Plan("Navigate", result.target, route="climb", on_ladder=True, platform=result.platform)
        return result

    def unstick_climb(self, result, player, mapper):  # Climbing with no progress for a while (a rope with nothing at the top, or
        # held against something): jump off instead, toward the middle of the screen where there's usually more map
        now = time.time()
        if result.route != "climb":
            self.climb_since = None
            return result
        feet = mapper.feet if mapper is not None else None  # Map coords: the camera follows the player, so screen height doesn't change
        height = feet[1] if feet is not None else None
        if self.climb_since is None:
            self.climb_since, self.climb_best, self.climb_progress = now, height, now
        elif height is not None and (self.climb_best is None or height < self.climb_best - climb_progress):
            self.climb_best, self.climb_progress = height, now
        stuck = now - self.climb_progress > climb_stuck_time if height is not None else now - self.climb_since > climb_max_time
        if not stuck:
            return result
        self.climb_since = None
        window = values.window_rect
        middle = (window[0] + window[2]) / 2 if window is not None else player.center_x
        result.route, result.dx = "jump_off", (1 if player.center_x <= middle else -1)
        return result

    def explore(self, mobs_in_sight, player, mapper):  # With Random Behaviour on, "up"/"down" once no mobs have been in sight for
        # explore_delay, else None.
        # Each leg ends on reaching another platform, then it waits explore_delay there before going on
        now = time.time()
        if mobs_in_sight or player is None or not values.randomizer_active:  # Without Random Behaviour: wait here for respawns
            self.last_mob_seen, self.explore_from, self.explore_goal = now, None, None
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


    def find_player(self, instances):  # The player found by their nametag, or None if it isn't visible
        if values.player_rect is None:
            return None
        x1, y1, x2, y2 = values.player_rect
        return rects.Rect("Player", "blue", x1, y1, x2, y2, 1)


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
