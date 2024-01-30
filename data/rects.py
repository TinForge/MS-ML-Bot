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
            if abs(rect.y1 - player.y2) < 30:
                return rect
    return None


def find_mobs_on_platform(rects, platform):
    mob_instances = [rect for rect in rects if (platform.x1 <= rect.center_x and platform.x2 >= rect.center_x) and (abs(platform.y1 - rect.y2) < 30)]
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


def find_closest_path(rects, platform):
    closest_distance = float('inf')
    closest_rect = None

    jump_height = 100

    for rect in rects:
        if rect.name == "Platform" or rect.name == "Ladder":
            if rect is not platform:
                if platform.y2 - rect.y1 < jump_height:  # if rect is higher or equal height
                    if platform.center_y - rect.center_y < jump_height and platform.center_y - rect.center_y > 0:  # if rect is higher, again.
                        distance = math.sqrt((platform.center_x - rect.center_x)**2)
                        if distance < closest_distance:
                            closest_distance = distance
                            closest_rect = rect

    return closest_rect


# Test set of rects
test_rects = [Rect("Example 1", "green", 100, 100, 200, 200, 1), Rect("Example 2", "red", 300, 300, 400, 400, 1), Rect("Example 3", "purple", 500, 500, 600, 600, 1)]
