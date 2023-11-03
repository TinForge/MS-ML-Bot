from data import rects

max_missed = 10
valid_threshold = 2
invalid_threshold = 3
cache_size = 2


class Tracker:
    def __init__(self, rect):
        self.name = rect.name
        self.color = rect.color
        self.list = [rect]
        self.missed = 0
        self.consecutive = 0
        self.valid = False
        self.flag = True
        self.dispose = False

    def add(self, rect):
        self.list.insert(0, rect)
        self.list = self.list[:cache_size]
        self.flag = True

    def prime(self):
        self.flag = False

    def process(self):
        if self.flag is True:
            self.consecutive += 1
            self.missed = 0
        else:
            self.consecutive = 0
            self.missed += 1
        if self.consecutive > valid_threshold:  # Show
            self.valid = True
        if self.missed > invalid_threshold:  # Hide
            self.valid = False
        if self.missed > max_missed:  # Delete
            self.dispose = True

    def average(self):
        x1 = sum(rect.x1 for rect in self.list)
        x1 = x1 / len(self.list)

        y1 = sum(rect.y1 for rect in self.list)
        y1 = y1 / len(self.list)

        x2 = sum(rect.x2 for rect in self.list)
        x2 = x2 / len(self.list)

        y2 = sum(rect.y2 for rect in self.list)
        y2 = y2 / len(self.list)

        return rects.Rect(self.name, self.color, x1, y1, x2, y2)

    def center_x(self):
        r = self.average()
        x = (r.x1 + r.x2) / 2
        return x

    def center_y(self):
        r = self.average()
        y = (r.y1 + r.y2) / 2
        return y

    def size(self):        
        r = self.average()
        s = (r.x2 - r.x1) * (r.y2 - r.y1)
        return s