
max_missed = 10
valid_threshold = 5

proximity_threshold = 5
size_threshold = 5


class Tracker:
    def __init__(self, rect):
        self.name = rect.name
        self.color = rect.color
        self.list = [rect]
        self.missed = 0
        self.consecutive = 0

    def add(self, rect):
        self.list.insert(0, rect)
        self.list = self.list[:5]
