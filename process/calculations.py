# Thread for calculating data

import time
import threading
from gui import window
from data import config, values, rects
from process import kills, navigation
from tools import map_recorder, movement, route_planner
from tools.route_planner import RoutePlanner
from tools import keyboard


climb_progress = 5  # Map pixels a climb must rise to count as getting somewhere
climb_stuck_time = 1.2  # Seconds climbing without rising before jumping off
climb_max_time = 6.0  # Longest climb when its progress can't be measured (map position unknown)
top_hold = 1.4  # Seconds Up stays held after a climb seems over: at a rope's top the platform overlaps it, so ground shows under
# the feet a moment before the character has stepped off
explore_min_width = 150  # Narrowest platform worth exploring to: single stair steps and scraps of recording aren't
jump_give_up = 3.0  # Seconds trying to jump up onto the same platform before taking it for out of reach
rope_top_margin = 40  # How far a platform's height may be from a rope's recorded top, and its end from the rope, to be the platform
# the rope leads up to
rope_jump_reach = 55  # Within this distance of a rope it's jumped at (straight up, or a running jump: behaviours.rope_run_jump)
jump_phase = 60  # Within this distance of a platform's edge the bot is jumping for it, not walking to it
unreachable_time = 15.0  # Seconds a platform that couldn't be jumped onto is left out of the routes up (a rope is used instead)
ROUTING = {"hunt": "Hunt nearest", "patrol": "Patrol up and down", "stay": "Stay on platform"}  # values.routing_mode: what it shows as
patrol_linger = 1.0  # Patrol: seconds a cleared platform is watched before moving on, so a mob missed for a moment isn't left behind
level_step = navigation.feet_margin  # Patrol: how much higher or lower a platform must be to count as the next level up or down
patrol_lone_reach = 200  # Patrol: a platform's only mob, farther than this, is left for later: climbing on is worth more than a walk to
# the platform's edge for one mob. Two or more are gone after wherever they are
safe_spot_width = 60  # Narrowest safe stretch of platform to retreat to: room to stand without a mob at its edge reaching the player
arrive_margin = 10  # How close to the middle of the safe stretch counts as there


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
        self.last_seen = None  # Player rect where the nametag was last found
        self.rope_bound = False  # The last plan with the player in sight was climbing, or jumping at a rope from under it
        self.climb_side = 0  # While climbing: which way (-1 left, 1 right) the middle of the platform at the rope's top is, 0 if unknown
        self.retreat_spot = None  # (platform, map x) being retreated to; False when no safe spot is known
        self.mode = None  # The routing mode the state below is for
        self.home = None  # Stay: (map id, feet map point) of the platform to stay on, taken when botting starts or the mode is picked
        self.was_botting = False
        self.patrol_direction = "up"  # Patrol: which way the next platform is looked for; turns round at the top and bottom
        self.patrol_goal = None  # Patrol: map point on the platform being headed for
        self.cleared_since = None  # Patrol: when the platform it's on was last seen without mobs to fight


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
        mode = self.sync_mode()
        if values.retreating:  # Low on potions: away from the mobs instead of fighting them
            result = self.retreat(player, instances, mapper, standing, state == movement.LADDER)
        elif mode in ("stay", "patrol"):
            self.retreat_spot = None
            result = self.keep_to_platforms(mode, player, instances, mapper, standing, state == movement.LADDER, skip, router)
        else:
            self.retreat_spot = None
            result = navigation.plan(player, instances, values.nav_jump_height, values.nav_clump_range, self.last_target, explore, standing,
                                     state == movement.LADDER, skip, router)
        result = self.hidden_on_rope(result)
        result = self.unstick_climb(result, player, mapper)
        result = self.finish_climb(result)
        result = self.toward_the_top(result, instances)
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
        values.debug_ledges = self.ledges(mapper) if result.state == "Attack" and standing else None
        values.debug_direction = keyboard.VK_LEFT if result.dx < 0 else keyboard.VK_RIGHT
        if result.state == "Attack":
            values.debug_crowd = result.crowd
            values.debug_center_dx = result.target.center_x - player.center_x
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

    def ledges(self, mapper):  # (left, right) distances from the feet to the ledges of the recorded platform stood on, None if unknown
        planner = self.route_planner(mapper)
        feet = mapper.feet if planner is not None else None
        line = planner.line_at(*feet) if feet is not None else None
        return planner.ledges(line, feet[0]) if line is not None else None

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
        return self.hop_step(hops[0], mapper, shift)

    def hop_step(self, hop, mapper, shift):  # A route's hop as a navigation.Step in screen coords
        dx, dy = shift
        if hop.kind == "rope":
            ladder = mapper.ladders[hop.ladder]
            x = ladder["x"] + dx
            target = rects.Rect("Ladder", "yellow", x - map_recorder.ladder_width / 2, ladder["top"] + dy, x + map_recorder.ladder_width / 2,
                                ladder["bottom"] + dy, 1)
        else:
            target = rects.PlatformLine([(x + dx, y + dy) for x, y in mapper.lines[hop.to]])
        return navigation.Step(hop.kind, target, hop.x1 + dx, hop.x2 + dx)

    def retreat(self, player, instances, mapper, standing, on_rope):  # To the middle of the nearest safe stretch of platform, ignoring
        # mobs; sets values.retreat_arrived once there, or straight away when no safe spot is known
        if player is None:
            return navigation.Plan("Search")
        platform = rects.find_player_platform(rects.find_platform_instances(instances), player)
        planner = self.route_planner(mapper)
        shift = mapper.screen_shift(mapper.frame_rect) if planner is not None else None
        feet = mapper.feet if shift is not None else None
        if feet is None:  # No recorded map to find a safe spot on: stop where it is
            values.retreat_arrived = True
            return navigation.Plan(platform=platform)
        start = planner.line_at(*feet)
        if start is None:  # On a rope or in the air: climb on up, or land first
            return navigation.plan(player, [r for r in instances if r.name != "Mob"], values.nav_jump_height, standing=standing, on_rope=on_rope)
        if self.retreat_spot is None:
            self.retreat_spot = self.safe_spot(planner, mapper, start, feet[0]) or False
        if not self.retreat_spot:
            values.retreat_arrived = True
            return navigation.Plan(platform=platform)
        line, x = self.retreat_spot
        dx, dy = shift
        if planner.same_platform(line, start):  # On it: walk to the middle
            distance = x + dx - player.center_x
            if abs(distance) <= arrive_margin:
                values.retreat_arrived = True
                return navigation.Plan(platform=platform)
            target = rects.PlatformLine([(px + dx, py + dy) for px, py in mapper.lines[line]])
            return navigation.Plan("Navigate", target, route="walk", dx=distance, platform=platform)
        avoid = self.unreachable_lines(mapper, shift) if self.unreachable else set()
        hops = planner.route(start, feet[0], line, avoid)
        if not hops:  # No way there after all (a jump kept failing): pick again next time
            self.retreat_spot = None
            return navigation.Plan(platform=platform)
        values.planned_route = planner.path(start, feet[0], hops)
        return navigation.step_plan(player, self.hop_step(hops[0], mapper, shift), platform, None)

    def sync_mode(self):  # The routing mode, started afresh when it's picked again or botting starts (Stay takes its home again)
        mode = values.routing_mode
        if mode != self.mode or (values.bot_active and not self.was_botting):
            self.mode, self.home, self.patrol_goal, self.cleared_since = mode, None, None, None
        self.was_botting = values.bot_active
        return mode

    def keep_to_platforms(self, mode, player, instances, mapper, standing, on_rope, skip, router):  # Stay and Patrol: fight only the
        # mobs on the platform kept to (Stay: its home platform; Patrol: the one it's on), then move as the mode says
        planner = self.route_planner(mapper)
        shift = mapper.screen_shift(mapper.frame_rect) if planner is not None else None
        feet = mapper.feet if shift is not None else None
        start = planner.line_at(*feet) if feet is not None else None
        if mode == "stay" and start is not None and (self.home is None or self.home[0] != mapper.map_id):
            self.home = (mapper.map_id, feet)
        home = planner.line_at(*self.home[1]) if mode == "stay" and self.home is not None and planner is not None else None
        kept = home if mode == "stay" else start  # The platform whose mobs it fights
        mobs = [r for r in instances if r.name == "Mob"]
        if kept is not None:
            dx, dy = shift
            on_kept = lambda m: (line := planner.line_at(m.center_x - dx, m.y2 - dy)) is not None and planner.same_platform(line, kept)
            mobs = [m for m in mobs if on_kept(m)]
            if mode == "patrol" and player is not None:
                mobs = self.patrol_targets(mobs, player)
        else:  # In the air, on a rope, or no recorded map: only mobs on the ground under it
            platform = rects.find_player_platform(rects.find_platform_instances(instances), player) if player is not None else None
            mobs = rects.find_mobs_on_platform(mobs, platform) if platform is not None and (mode == "patrol" or planner is None) else []
        result = navigation.plan(player, [r for r in instances if r.name != "Mob"] + mobs, values.nav_jump_height, values.nav_clump_range,
                                 self.last_target, None, standing, on_rope, skip, router)
        if result.state is not None or start is None:  # Fighting, searching for the player or on a rope: as planned
            if result.state == "Attack":
                self.cleared_since = None
            return result
        if mode == "stay":
            if home is None or planner.same_platform(home, start):
                return result  # Home, with nothing to fight: wait for mobs
            return self.head_for(player, mapper, planner, shift, start, feet, home, result.platform)
        return self.patrol(player, mapper, planner, shift, start, feet, result.platform)

    def patrol_targets(self, mobs, player):  # Patrol: the mobs worth fighting on the platform it's on. On the way down to the bottom,
        # only those already in attack range; on the way up, all of them, but a lone one far off
        reach = lambda m: abs(navigation.near_edge_dx(m, player))
        if self.patrol_direction == "down" and self.patrol_goal is not None:
            return [m for m in mobs if reach(m) <= values.nav_attack_range]
        if len(mobs) == 1 and reach(mobs[0]) > patrol_lone_reach:
            return []
        return mobs

    def patrol(self, player, mapper, planner, shift, start, feet, platform):  # Cleared this platform: on to the next one up, or down
        now = time.time()
        goal = planner.line_at(*self.patrol_goal) if self.patrol_goal is not None else None
        if goal is None or planner.same_platform(goal, start):  # Arrived (or the goal is gone from the recording)
            if self.patrol_goal is not None:
                self.patrol_goal, self.cleared_since = None, now
            if self.cleared_since is None:
                self.cleared_since = now
            if now - self.cleared_since < patrol_linger:  # Watch for mobs here a moment before moving on
                return navigation.Plan(platform=platform)
            self.patrol_goal = self.next_level(planner, mapper, start, feet[0])
            goal = planner.line_at(*self.patrol_goal) if self.patrol_goal is not None else None
            if goal is None:  # Nowhere else to go
                return navigation.Plan(platform=platform)
        return self.head_for(player, mapper, planner, shift, start, feet, goal, platform)

    def next_level(self, planner, mapper, start, x):  # Map point in the middle of the next platform up (patrol_direction): the nearest
        # level, then the quickest to get to. At the top it turns round and heads straight for the bottom: the lowest platform it can
        # get to; there it turns round again. None if there's no other platform
        reachable = planner.routes(start, x)
        here = planner.height(start, x)
        for _ in range(2):
            up = self.patrol_direction == "up"
            levels = []
            for line, (seconds, _) in reachable.items():
                if planner.same_platform(line, start) or planner.width(line) < explore_min_width:  # Not stair steps or scraps
                    continue
                points = mapper.lines[line]
                middle = (points[0][0] + points[-1][0]) / 2
                rise = here - planner.height(line, middle)  # Map y grows downwards
                if rise > level_step if up else rise < -level_step:  # Lowest rise first: up, the nearest level; down, the lowest
                    levels.append((rise, seconds, (middle, planner.height(line, middle))))
            if levels:
                return min(levels)[2]
            self.patrol_direction = "down" if up else "up"
        return None

    def head_for(self, player, mapper, planner, shift, start, feet, line, platform):  # The first step of the route to that platform
        avoid = self.unreachable_lines(mapper, shift) if self.unreachable else set()
        hops = planner.route(start, feet[0], line, avoid)
        if not hops:  # No way there (a jump kept failing): wait, and the next look may find one
            self.patrol_goal = None
            return navigation.Plan(platform=platform)
        values.planned_route = planner.path(start, feet[0], hops)  # For the overlay's Route option
        return navigation.step_plan(player, self.hop_step(hops[0], mapper, shift), platform, None)

    def safe_spot(self, planner, mapper, start, x):  # (platform, map x) of the middle of the nearest safe stretch, failing that the
        # nearest only occasionally visited by mobs; None when neither has been learned yet
        reachable = planner.routes(start, x)
        for safety in (map_recorder.SAFE, map_recorder.OCCASIONAL):
            best = None
            for line, (seconds, _) in reachable.items():
                for x1, x2 in mapper.platforms.stretches(mapper.lines[line], safety, safe_spot_width):
                    middle = (x1 + x2) / 2
                    walk = abs(middle - x) / route_planner.walk_speed if planner.same_platform(line, start) else 0.0
                    if best is None or seconds + walk < best[0]:
                        best = (seconds + walk, line, middle)
            if best is not None:
                return best[1], best[2]
        return None

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

    def unreachable_lines(self, mapper, shift):  # Recorded platforms whose jumps kept failing, and ("rope", index) of ropes that couldn't
        # be caught
        dx, dy = shift
        lines = [rects.PlatformLine([(x + dx, y + dy) for x, y in line]) for line in mapper.lines]
        avoid = {i for i, line in enumerate(lines) if self.platform_key(line, mapper) in self.unreachable}
        for j, ladder in enumerate(mapper.ladders):
            x = ladder["x"] + dx
            rope = rects.Rect("Ladder", "yellow", x - map_recorder.ladder_width / 2, ladder["top"] + dy, x + map_recorder.ladder_width / 2,
                              ladder["bottom"] + dy, 1)
            if self.platform_key(rope, mapper) in self.unreachable:
                avoid.add(("rope", j))
        return avoid

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
        return [r for r in instances if r.name in ("Platform", "Ladder") and self.platform_key(r, mapper) in self.unreachable]

    def watch_jumps(self, result, mapper):  # Trying to jump up onto the same platform or rope for too long: it's out of reach after all
        target = result.target
        if result.route != "up" or target is None or target.name not in ("Platform", "Ladder") or abs(result.dx) > jump_phase:
            self.jump_key = None  # Not jumping for one (still walking to it doesn't count)
            return
        now, key = time.time(), self.platform_key(target, mapper)
        if key != self.jump_key:
            self.jump_key, self.jump_since = key, now
        elif now - self.jump_since > jump_give_up:
            self.unreachable[key] = now + unreachable_time
            self.jump_key = None

    def hidden_on_rope(self, result):  # The nametag hidden (a rope's art covers it) just as it jumped at a rope or while climbing: keep
        # climbing. The last position seen is still at the rope's foot, so the plan would have it stand there; it reappears at the top
        if values.player_rect is not None or self.last_seen is None:
            self.rope_bound = result.route == "climb" or (result.route == "up" and result.on_ladder and abs(result.dx) <= rope_jump_reach)
            return result
        if self.rope_bound:
            return navigation.Plan("Navigate", result.target, route="climb", on_ladder=True, platform=result.platform)
        return result

    def toward_the_top(self, result, instances):  # Climbing: the side the platform at the rope's top lies on (toward its middle), as
        # the plan's dx. The arrow held with Up does nothing on the rope, but walks it off at the top: standing at the top under the
        # rope's art, the nametag stayed hidden and the bot kept climbing, stuck
        if result.route != "climb":
            self.climb_side = 0
            return result
        rope = result.target
        if rope is not None and rope.name == "Ladder" and rope.y2 > rope.y1:  # A recorded rope (a stand-in has no top): the platform there
            x = rope.center_x
            tops = [p for p in instances if p.name == "Platform" and p.x1 - rope_top_margin <= x <= p.x2 + rope_top_margin
                    and abs(p.top_at(min(max(x, p.x1), p.x2)) - rope.y1) <= rope_top_margin]
            if tops:
                top = min(tops, key=lambda p: abs(p.top_at(min(max(x, p.x1), p.x2)) - rope.y1))
                self.climb_side = -1 if top.center_x < x else 1
        result.dx = self.climb_side  # Kept from the rope while the target is something else (the nametag hidden, or the hold at the top)
        return result

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


    def find_player(self, instances):  # The player found by their nametag; while it's covered (a mob or skill effect over it), where it
        # was last seen, so navigation and fighting carry on. The camera follows the player, so they stay about there on screen. None
        # only before it has ever been found
        if values.player_rect is not None:
            self.last_seen = values.player_rect
        rect = self.last_seen
        if rect is None:
            return None
        x1, y1, x2, y2 = rect
        return rects.Rect("Player", "blue", x1, y1, x2, y2, 1)


    def clear_values(self):
        values.debug_player = None
        values.debug_platform = None
        values.debug_mob = None
        values.debug_path = None
        values.debug_route = None
        values.debug_on_ladder = False
        values.debug_ledges = None
        values.debug_x_distance = 0
        values.debug_y_distance = 0
        values.debug_direction = None


instance: CalculationThread = None
