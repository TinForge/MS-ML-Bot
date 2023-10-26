# Data container for rect bounds
import math


class Rect:
    def __init__(self, name, color, x1, y1, x2, y2):
        self.name = name
        self.color = color
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.center_x = (self.x1 + self.x2) / 2
        self.center_y = (self.y1 + self.y2) / 2


def compare_distance(rect1, rect2):
    distance = math.sqrt((rect2.center_x - rect1.center_x)**2 + (rect2.center_y - rect1.center_y)**2)
    return distance


def find_mob_instances(rects):
    mob_instances = [obj for obj in rects if obj.name == "Mob"]
    return mob_instances


def filter_mobs_by_height(rects, player, threshold):
    mob_instances = [obj for obj in rects if abs(obj.center_y - player.center_y) < threshold]
    return mob_instances


def find_closest_mob(detections, player):
    closest_distance = float('inf')
    closest_rect = None

    for rect in detections:
        if rect.name == "Mob":
            distance = compare_distance(rect, player)
            if distance < closest_distance:
                closest_distance = distance
                closest_rect = rect

    return closest_rect


def find_rect_by_class(detections, class_name):
    for rect in detections:
        if rect.name == class_name:
            return rect
    return None


# Test set of rects
test_rects = [Rect("Example 1", "green", 100, 100, 200, 200), Rect("Example 2", "red", 300, 300, 400, 400), Rect("Example 3", "purple", 500, 500, 600, 600)]
