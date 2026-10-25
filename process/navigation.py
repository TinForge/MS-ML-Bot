# Decides where the player should go from what's on screen: attack, or move up, down or across towards mobs

from dataclasses import dataclass

from data import rects

feet_margin = 30  # How far feet may be from a platform's top while still standing on it
edge_overlap = 30  # How far the player may overlap a platform above before jumping straight up for it
drop_margin = 15  # How far inside a lower platform's edges the player must be before dropping onto it


@dataclass
class Plan:
    state: str = None  # Attack, Navigate, Search, or None when there's nothing to do
    target: object = None  # Mob to attack, or platform/ladder to move to
    route: str = None  # Navigate: up (jump onto target), down (drop onto target) or walk (towards a mob)
    dx: float = 0  # Horizontal distance to the target: negative is left
    dy: float = 0  # How far the target is above the player
    on_ladder: bool = False  # Navigate target is a ladder
    platform: object = None  # Platform the player stands on
    goal: object = None  # Mob the route leads towards


def plan(player, instances, jump_height):  # player is a Rect, or None when the player can't be found
    if player is None:
        return Plan("Search")
    platforms = rects.find_platform_instances(instances)
    mobs = rects.find_mob_instances(instances)
    platform = rects.find_player_platform(platforms, player)

    # Attack mobs on the player's platform (or any mob, if no platform is detected under the player)
    local_mobs = rects.find_mobs_on_platform(mobs, platform) if platform is not None else mobs
    mob = rects.find_closest_mob(local_mobs, player)
    if mob is not None:
        return Plan("Attack", mob, dx=mob.center_x - player.center_x, dy=player.center_y - mob.center_y, platform=platform)

    goal = rects.find_closest_mob(mobs, player)  # Nearest mob elsewhere, which the route heads for
    if goal is not None and goal.y2 > player.y2 + feet_margin:  # Goal is lower down
        below = find_platform_below(platforms, player, goal)
        if below is not None:
            return drop_plan(player, below, platform, goal)

    path = rects.find_closest_path(instances, player, jump_height, goal, exclude=platform)
    if path is not None:
        return up_plan(player, path, platform, goal)

    if goal is not None:
        return Plan("Navigate", goal, route="walk", dx=goal.center_x - player.center_x, platform=platform, goal=goal)

    below = find_platform_below(platforms, player, None)  # Nothing to do up here: explore downwards
    if below is not None:
        return drop_plan(player, below, platform, None)
    return Plan(platform=platform)


def find_platform_below(platforms, player, goal):  # Lower platform to drop onto: the goal's own if visible, else the one right underneath
    below = [p for p in platforms if p.y1 > player.y2 + feet_margin]
    if not below:
        return None
    if goal is not None:
        goal_platform = rects.find_player_platform(below, goal)
        if goal_platform is not None:
            return goal_platform
    underneath = [p for p in below if p.x1 <= player.center_x <= p.x2]
    if underneath:
        return min(underneath, key=lambda p: p.y1)  # Dropping lands on the highest one
    return min(below, key=lambda p: abs(p.center_x - player.center_x) + (p.y1 - player.y2))


def drop_plan(player, target, platform, goal):  # Walk into the target's x range, then drop
    x = player.center_x
    left, right = target.x1 + drop_margin, target.x2 - drop_margin
    dx = 0 if left <= x <= right else (left - x if x < left else right - x)
    return Plan("Navigate", target, route="down", dx=dx, dy=player.y2 - target.y1, platform=platform, goal=goal)


def up_plan(player, path, platform, goal):  # Walk to the path's edge, then jump onto it
    if player.center_x < path.center_x:  # player is left of the path
        x = path.x1 - player.x2
        dx = 0 if x < -edge_overlap else x  # close enough to jump straight up
    else:  # player is right of the path
        x = path.x2 - player.x1
        dx = 0 if x > edge_overlap else x
    on_ladder = path.name == "Ladder"
    dy = player.y2 - path.y2 if on_ladder else player.y2 - path.y1
    return Plan("Navigate", path, route="up", dx=dx, dy=dy, on_ladder=on_ladder, platform=platform, goal=goal)
