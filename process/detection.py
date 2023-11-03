# Thread for detecting models

from gui import window
import time
import threading
import math

from data import values
from data import trackers
from yolov5 import model


class DetectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.model = model.Model()

    def run(self):
        while window.instance is not None:
            if self.is_running is False:
                time.sleep(0.01)  # Adjustable
            else:
                time.sleep(0.01)  # Adjustable
                detections = self.model.run(True, False)
                values.detected_instances = detections
                self.process()


    def process(self):
        containers = values.detected_trackers

        for tracker in containers:
            tracker.prime()

        for rect in values.detected_instances:
            matching_trackers = [tracker for tracker in containers if tracker.name == rect.name]
            ordered_trackers = sorted(matching_trackers, key=lambda r: math.sqrt((r.center_x() - rect.center_x)**2 + (r.center_y() - rect.center_y)**2))
            if len(ordered_trackers) != 0:
                similarity = min(rect.size, ordered_trackers[0].size()) / max(rect.size, ordered_trackers[0].size()) * 100
                if similarity >= 75:
                    ordered_trackers[0].add(rect)
                else:
                    containers.append(trackers.Tracker(rect))
            else:
                containers.append(trackers.Tracker(rect))

        for tracker in containers[:]:
            tracker.process()
            if tracker.dispose is True:
                containers.remove(tracker)
                del tracker

        values.detected_trackers = containers

        #   prime trackers first
        #   sweep through every rect first
        #   for each rect, find a tracker
        #   search by rect's classification
        #   search in order of proximity
        #   if none found, create a tracker
        #   if matched, increment tracker
        #   process trackers at end


instance: DetectionThread = None
