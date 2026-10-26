# Decides where the player should go from what's on screen: attack, or move up, down or across towards mobs

from dataclasses import dataclass

from data import rects

feet_margin = 30  # How far feet may be from a platform's top while still standing on it
edge_overlap = 30  # How far the player may overlap a platform above before jumping straight up for it
drop_margin = 15  # How far inside a lower platform's edges the player must be before dropping onto it
ladder_align = 20  # How far the player's centre may be from a rope's before jumping straight up onto it (ropes catch well off-centre)
on_ladder_x = 20  # How far the player's centre may be from a rope's while hanging on it (the tracker takes a moment to say so)
height_weight = 3  # When picking a target, height difference counts this many times more than horizontal distance (prefer the same level)
clump_bonus = 40  # When picking a target, each other mob in the same direction and within clump range counts as this much closer
hurt_bonus = 150  # When picking a target, a mob with its health bar showing (already hit) counts as this much closer: finish it first
stick_bonus = 40  # When picking a target, the one picked last counts as this much closer, so two similar mobs don't swap every frame
stick_distance = 40  # How far the last target may have moved (knockback, box jitter) and still be the one picked last
size_weight = 0.5  # When picking a target, each pixel of width beyond typical_width counts as this much closer (negative: prefer smaller)
typical_width = 50  # Mob box width that size_weight counts from


@dataclass
class Plan:
    state: str = None  # Attack, Navigate, Search, or None when there's nothing to do
    target: object = None  # Mob to attack, or platform/ladder to move to
    route: str = None  # Navigate: up (jump onto target), down (drop onto target), walk (towards a mob), climb (up the rope it's on) or
    # jump_off (off the rope, sideways: dx gives the side)
    dx: float = 0  # Horizontal distance to the target: negative is left. Attack: to the mob's nearer edge
    dy: float = 0  # How far the target is above the player
    on_ladder: bool = False  # Navigate target is a ladder
    platform: object = None  # Platform the player stands on
    crowd: list = None  # Attack: (dx to the mob's nearer edge, dy) of every mob on screen, the target included, for mobbing attacks
    goal: object = None  # Mob the route leads towards


def plan(player, instances, jump_height, clump_range=150, previous=None, explore=None, standing=None, on_rope=False, skip=()):  # player: a
    # Rect, None when the player can't be found. clump_range: how far in front the widest-hitting attack reaches, for preferring
    # bunched-up mobs; previous: the last plan's target; explore: "up" or "down" to look for mobs on other platforms when none are in
    # sight; standing / on_rope: what the movement tracker says the player is doing (on the ground / hanging on a rope); skip: platforms
    # not to jump for, as jumps at them kept failing
    if player is None:
        return Plan("Search")
    platforms = rects.find_platform_instances(instances)
    mobs = rects.find_mob_instances(instances)
    platform = rects.find_player_platform(platforms, player)
    ladder = hanging_on(instances, player, platform, standing, on_rope)
    if ladder is not None:  # Nothing else can be done from a rope: climb on up, or jump off toward a mob lower down
        return rope_plan(player, ladder, platform, pick_target(rects.find_mob_instances(instances), player, 0))

    # Attack mobs on the player's platform (or any mob, if no platform is detected under the player)
    local_mobs = rects.find_mobs_on_platform(mobs, platform) if platform is not None else mobs
    mob = pick_target(local_mobs, player, clump_range, previous)
    if mob is not None:
        crowd = [(near_edge_dx(m, player), player.center_y - m.center_y) for m in mobs]  # Every mob: range_y decides which levels it hits
        dx = near_edge_dx(mob, player)  # 0 when the mob overlaps the player: attacked whichever way the character faces
        return Plan("Attack", mob, dx=dx, dy=player.center_y - mob.center_y, platform=platform, crowd=crowd)

    goal = pick_target(mobs, player, 0)  # Nearest mob elsewhere, which the route heads for
    if goal is None:
        return explore_plan(instances, platforms, player, platform, jump_height, explore, skip)
    if goal.y2 > player.y2 + feet_margin:  # Lower down: drop
        below = find_platform_below(platforms, player, goal)
        if below is not None:
            return drop_plan(player, below, platform, goal)
    elif standing_above(platforms, player, goal):  # On a platform higher up: jump or climb, but only then. Not just a higher box
        # bottom: flying mobs and sprites drawn above their feet would send the bot up the nearest rope
        path = rects.find_closest_path(instances, player, jump_height, goal, exclude=platform, skip=skip)
        if path is not None:
            return up_plan(player, path, platform, goal)
    return Plan("Navigate", goal, route="walk", dx=goal.center_x - player.center_x, platform=platform, goal=goal)


def explore_plan(instances, platforms, player, platform, jump_height, direction, skip=()):  # No mobs in sight. Exploring, head for the
    # nearest way up (rope or jump) or down; otherwise, or with no way that direction, stay put
    if direction == "up":
        path = rects.find_closest_path(instances, player, jump_height, None, exclude=platform, skip=skip)
        if path is not None:
            return up_plan(player, path, platform, None)
    elif direction == "down":
        below = find_platform_below(platforms, player, None)
        if below is not None:
            return drop_plan(player, below, platform, None)
    return Plan(platform=platform)


def hanging_on(instances, player, platform, standing, on_rope=False):  # The rope the player is hanging on, or None. The movement
    # tracker knows it for sure (on_rope), even on a rope that was never recorded; otherwise a recorded rope where the player is
    if platform is not None or standing:  # On a platform: at most at a rope's foot or top (and Up there could take a portal)
        return None
    near = [r for r in instances if r.name == "Ladder" and abs(r.center_x - player.center_x) <= on_ladder_x
            and r.y1 - feet_margin <= player.y2 <= r.y2 + feet_margin]
    if near:
        return near[0]
    if on_rope:  # Not recorded: a stand-in where the player is
        return rects.Rect("Ladder", "yellow", player.center_x - on_ladder_x, player.y2, player.center_x + on_ladder_x, player.y2, 1)
    return None


def rope_plan(player, ladder, platform, goal):  # On a rope: climb up, unless the mob being headed for is lower down: then jump off
    # toward it, which is quicker than climbing down
    if goal is not None and goal.y2 > player.y2 + feet_margin:
        side = 1 if goal.center_x >= player.center_x else -1
        return Plan("Navigate", ladder, route="jump_off", dx=side, on_ladder=True, platform=platform, goal=goal)
    return Plan("Navigate", ladder, route="climb", dy=player.y2 - ladder.y1, on_ladder=True, platform=platform, goal=goal)


def standing_above(platforms, player, mob):  # Whether the mob stands on a known platform higher than the player's feet
    below_its_feet = [p for p in platforms if p.x1 <= mob.center_x <= p.x2 and abs(p.top_at(mob.center_x) - mob.y2) < feet_margin]
    return any(p.top_at(mob.center_x) < player.y2 - feet_margin for p in below_its_feet)


def near_edge_dx(mob, player):  # Horizontal distance to the mob's nearer edge, signed like its centre: an attack hits it from there.
    # 0 when the mob overlaps the player's centre
    dx = mob.center_x - player.center_x
    return 0 if abs(dx) <= (mob.x2 - mob.x1) / 2 else dx - (mob.x2 - mob.x1) / 2 * (1 if dx > 0 else -1)


def pick_target(mobs, player, clump_range, previous=None):  # The closest mob (to its nearer edge), favouring the same level, mobs
    # already hurt, the direction with more mobs bunched up, and the target picked last. Returns the nearest mob that way, as that's
    # the one an attack aimed that way hits first
    def ahead(m):  # Mobs on the same side as m and at its level
        dx = m.center_x - player.center_x
        return [o for o in mobs if (o.center_x - player.center_x) * dx >= 0 and abs(o.y2 - m.y2) <= feet_margin]

    def score(m):
        bunched = sum(1 for o in ahead(m) if abs(o.center_x - player.center_x) <= clump_range) - 1 if clump_range > 0 else 0
        hurt = m.health is not None
        kept = previous is not None and abs(m.center_x - previous.center_x) <= stick_distance and abs(m.y2 - previous.y2) <= stick_distance
        return (abs(near_edge_dx(m, player)) + height_weight * abs(m.y2 - player.y2) - clump_bonus * max(bunched, 0) - hurt_bonus * hurt
                - stick_bonus * kept - size_weight * ((m.x2 - m.x1) - typical_width))

    if not mobs:
        return None
    best = min(mobs, key=score)
    return min(ahead(best), key=lambda o: abs(o.center_x - player.center_x))


def find_platform_below(platforms, player, goal):  # Lower platform to drop onto: the goal's own if visible, else the one right underneath
    below = [p for p in platforms if p.top_at(player.center_x) > player.y2 + feet_margin]
    if not below:
        return None
    if goal is not None:
        goal_platform = rects.find_player_platform(below, goal)
        if goal_platform is not None:
            return goal_platform
    underneath = [p for p in below if p.x1 <= player.center_x <= p.x2]
    if underneath:
        return min(underneath, key=lambda p: p.top_at(player.center_x))  # Dropping lands on the highest one
    return min(below, key=lambda p: abs(p.center_x - player.center_x) + (p.top_at(player.center_x) - player.y2))


def drop_plan(player, target, platform, goal):  # Walk into the target's x range, then drop
    x = player.center_x
    left, right = target.x1 + drop_margin, target.x2 - drop_margin
    dx = 0 if left <= x <= right else (left - x if x < left else right - x)
    return Plan("Navigate", target, route="down", dx=dx, dy=player.y2 - target.top_at(x + dx), platform=platform, goal=goal)


def up_plan(player, path, platform, goal):  # Walk to the path's edge (a rope: its middle), then jump onto it
    if path.name == "Ladder":
        dx = path.center_x - player.center_x
        dx = 0 if abs(dx) <= ladder_align else dx  # Lined up: jump straight up, holding Up to grab it
        return Plan("Navigate", path, route="up", dx=dx, dy=player.y2 - path.y2, on_ladder=True, platform=platform, goal=goal)
    if player.center_x < path.center_x:  # player is left of the path
        x = path.x1 - player.x2
        dx = 0 if x < -edge_overlap else x  # close enough to jump straight up
    else:  # player is right of the path
        x = path.x2 - player.x1
        dx = 0 if x > edge_overlap else x
    dy = player.y2 - path.top_at(player.center_x + dx)
    return Plan("Navigate", path, route="up", dx=dx, dy=dy, platform=platform, goal=goal)
