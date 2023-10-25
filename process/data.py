
# Data container for rect bounds
class Rect:
    def __init__(self, name, color, x1, y1, x2, y2):
        self.name = name
        self.color = color
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2


# Test set of rects
test_rects = [Rect("Example 1", "green", 100, 100, 200, 200), Rect("Example 2", "red", 300, 300, 400, 400), Rect("Example 3", "purple", 500, 500, 600, 600)]
