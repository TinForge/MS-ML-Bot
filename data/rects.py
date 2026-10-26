# Data container for rect bounds
import math


class Rect:
    def __init__(self, name, color, x1, y1, x2, y2, confidence, timestamp=0):
        self.name = name
        self.color = color
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.center_x = (self.x1 + self.x2) / 2
        self.center_y = (self.y1 + self.y2) / 2
        self.size = (self.x2 - self.x1) * (self.y2 - self.y1)
        self.confidence = confidence
        self.timestamp = timestamp
        self.health = None  # Mobs: share of health left from the bar above them, None without one (see tools/mob_health.py)

    def top_at(self, x):  # Height of the top edge at x: flat for a box, see PlatformLine for slopes
        return self.y1

    def bottom_at(self, x):
        return self.y2


class PlatformLine(Rect):  # Recorded ground as a polyline [(x, y), ...] sorted by x, so slopes keep their height along the way
    def __init__(self, points, color="brown"):
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        super().__init__("Platform", color, min(xs), min(ys), max(xs), max(ys), 1)
        self.points = points

    def top_at(self, x):  # Ground height at x, held level past either end
        points = self.points
        if x <= points[0][0]:
            return points[0][1]
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            if x <= bx:
                return ay + (by - ay) * (x - ax) / (bx - ax) if bx > ax else by
        return points[-1][1]

    def bottom_at(self, x):  # A line has no thickness
        return self.top_at(x)


def find_rect_by_class(rects, class_name):
    for rect in rects:
        if rect.name == class_name:
            return rect
    return None


def compare_distance(rect1, rect2):
    distance = math.sqrt((rect2.center_x - rect1.center_x)**2 + (rect2.center_y - rect1.center_y)**2)
    return distance




def find_mob_instances(rects):
    mob_instances = [obj for obj in rects if obj.name == "Mob"]
    return mob_instances


def find_platform_instances(rects):
    mob_instances = [obj for obj in rects if obj.name == "Platform"]
    return mob_instances



def find_player_platform(rects, player):
    for rect in rects:
        if rect.x1 <= player.center_x and rect.x2 >= player.center_x:
            if abs(rect.top_at(player.center_x) - player.y2) < 30:
                return rect
    return None


def find_mobs_on_platform(rects, platform):
    mob_instances = [rect for rect in rects if (platform.x1 <= rect.center_x and platform.x2 >= rect.center_x) and (abs(platform.top_at(rect.center_x) - rect.y2) < 30)]
    return mob_instances


def filter_mobs_by_height(rects, player):
    mob_instances = [obj for obj in rects if abs(obj.center_y - player.center_y) < 150]
    return mob_instances


def find_closest_mob(rects, player):
    closest_distance = float('inf')
    closest_rect = None

    for rect in rects:
        if rect.name == "Mob":
            distance = compare_distance(rect, player)
            if distance < closest_distance:
                closest_distance = distance
                closest_rect = rect

    return closest_rect


def find_closest_path(rects, player, jump_height=100, goal=None, exclude=None):  # Nearest platform or ladder above within jump reach
    closest_distance = float('inf')
    closest_rect = None

    for rect in rects:
        if rect.name == "Platform" or rect.name == "Ladder":
            if rect is not player and rect is not exclude:
                if player.center_y - rect.bottom_at(player.center_x) > 0:  # if rect is not below
                    if (rect.name == "Platform" and player.y2 - rect.top_at(player.center_x) < jump_height) or (rect.name == "Ladder" and player.y2 - rect.y2 < jump_height):  # if rect is reachable
                        distance = abs(player.center_x - rect.center_x)
                        if goal is not None:  # Prefer paths that lead towards the goal
                            distance += abs(rect.center_x - goal.center_x)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_rect = rect

    return closest_rect


# Test set of rects
test_rects = [Rect("Example 1", "green", 100, 100, 200, 200, 1), Rect("Example 2", "red", 300, 300, 400, 400, 1), Rect("Example 3", "purple", 500, 500, 600, 600, 1)]
