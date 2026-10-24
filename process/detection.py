# Thread for detecting models

from gui import window
import time
import threading
import math

from data import values
from data import trackers
from tools import stat_reader, timer
from yolov5 import model

stats_interval = 0.25  # Seconds between HP/MP reads while detection is off


class DetectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.model = model.Model()
        self.last_stats_time = 0

    def run(self):
        while window.instance is not None:
            if self.is_running is False:
                time.sleep(0.01)  # Adjustable
                self.read_stats(None)
            else:
                time.sleep(0.01)  # Adjustable
                frame_start = time.perf_counter()
                detections = self.model.run(True, False)
                values.detected_instances = detections
                self.read_stats(self.model.last_frame)
                self.process()
                timer.record("Detection", frame_start)  # Total: grab, inference, HP/MP read and tracking


    def read_stats(self, frame):  # Reuses the inference frame when there is one, otherwise grabs at a slower rate
        if frame is None and time.time() - self.last_stats_time < stats_interval:
            return
        self.last_stats_time = time.time()
        start = time.perf_counter()
        if frame is not None:
            values.player_hp, values.player_mp = stat_reader.read_frame(frame)
        else:
            values.player_hp, values.player_mp = stat_reader.read(values.window_rect)
        timer.record("Stats", start)  # Includes its own screen grab while detection is off
        values.stats_read_id += 1  # Lets readers tell a fresh reading from one they've already seen


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

        # Use stable or velocity instances
        # values.detected_instances = [tracker.extrapolated_average() for tracker in containers]
        # values.detected_instances = [tracker.average() for tracker in containers]

        #   prime trackers first
        #   sweep through every rect first
        #   for each rect, find a tracker
        #   search by rect's classification
        #   search in order of proximity
        #   if none found, create a tracker
        #   if matched, increment tracker
        #   process trackers at end


instance: DetectionThread = None
