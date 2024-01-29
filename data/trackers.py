import time
from data import rects


cache_size = 3  # how many frames to track. 2 is more responsive, 3 stabilizes velocity
valid_threshold = 2  # how many positive IDs to display
invalid_threshold = 3  # how many missed frames to hide
max_missed = 10  # how many missed frames to delete tracker


class Tracker:
    def __init__(self, rect: rects.Rect):
        self.name = rect.name
        self.color = rect.color
        self.list = [rect]
        self.missed = 0
        self.consecutive = 0
        self.valid = False
        self.flag = True
        self.dispose = False

    # Add a rect to the tracker
    def add(self, rect):
        self.list.insert(0, rect)
        self.list = self.list[:cache_size]
        self.flag = True

    # Set every frame to perform operations
    def prime(self):
        self.flag = False

    # Calculates tracker's state
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

    # Returns the averaged/stable rects
    def average(self):
        x1 = sum(rect.x1 for rect in self.list)
        x1 = x1 / len(self.list)

        y1 = sum(rect.y1 for rect in self.list)
        y1 = y1 / len(self.list)

        x2 = sum(rect.x2 for rect in self.list)
        x2 = x2 / len(self.list)

        y2 = sum(rect.y2 for rect in self.list)
        y2 = y2 / len(self.list)

        confidence = sum(rect.confidence for rect in self.list)      
        confidence = round(confidence / len(self.list), 2)

        return rects.Rect(self.name, self.color, x1, y1, x2, y2, confidence)

    # Returns the velocity extrapolated rects
    def extrapolated_average(self):
        total_distance_x = 0
        total_distance_y = 0
        total_time = 0

        if len(self.list) <= cache_size:
            return self.average()

        for i in range(cache_size - 1, 0, -1):
            # Get the current and previous coordinate
            curr_coord = self.list[i]
            prev_coord = self.list[i - 1]

            # Calculate distance between the coordinates in the x and y directions
            distance_x = curr_coord.center_x - prev_coord.center_x
            distance_y = curr_coord.center_y - prev_coord.center_y

            # Calculate time difference between the timestamps
            time_diff = curr_coord.timestamp - prev_coord.timestamp

            # Accumulate total distance in the x and y directions and total time
            total_distance_x += distance_x
            total_distance_y += distance_y
            total_time += time_diff

        if total_time == 0:
            average_velocity_x = 0
            average_velocity_y = 0
        else:
            # Calculate average velocity components in the x and y directions
            average_velocity_x = total_distance_x / total_time
            average_velocity_y = total_distance_y / total_time

        current_timestamp = int(time.time() * 1000)
        initial_timestamp = self.list[0].timestamp
        time_elapsed = current_timestamp - initial_timestamp
        average_velocity_x *= time_elapsed
        average_velocity_y *= time_elapsed

        confidence = sum(rect.confidence for rect in self.list)
        confidence = round(confidence / len(self.list), 2)

        return rects.Rect(self.name, self.color, self.list[0].x1 + average_velocity_x, self.list[0].y1 + average_velocity_y, self.list[0].x2 + average_velocity_x, self.list[0].y2 + average_velocity_y, confidence)


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