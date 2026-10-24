# Thread for detecting models

from gui import window
import time
import threading
import math

from PIL import ImageGrab

from data import values
from data import trackers
from tools import stat_reader, player_finder, timer

stats_interval = 0.25  # Seconds between HP/MP reads while detection is off


class DetectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.model = None  # Loaded the first time detection runs, as importing torch and YOLOv5 takes seconds
        self.last_stats_time = 0

    def run(self):
        while window.instance is not None:
            if self.is_running is False:
                time.sleep(0.01)  # Adjustable
                self.read_stats(None, None)
            elif self.model is None:
                self.load_model()
            else:
                time.sleep(0.01)  # Adjustable
                frame_start = time.perf_counter()
                detections = self.model.run(True, False)
                values.detected_instances = detections
                self.read_stats(self.model.last_frame, self.model.last_frame_rect)
                self.process()
                timer.record("Detection", frame_start)  # Total: grab, inference, HP/MP read, player find and tracking


    def load_model(self):
        try:
            from yolov5 import model  # Imported here so the app starts without torch
            self.model = model.Model()
        except Exception as e:
            print("Failed to load the detection model:", e)
            self.is_running = False


    def read_stats(self, frame, frame_rect):  # Reuses the inference frame when there is one, otherwise grabs at a slower rate
        if frame is None:
            if time.time() - self.last_stats_time < stats_interval:
                return
            frame_rect = values.window_rect
            full = values.show_player_rect  # Finding the player needs the whole game area, the stats only its bottom
        else:
            full = True
        self.last_stats_time = time.time()
        start = time.perf_counter()
        if frame is None and frame_rect is not None:
            frame = ImageGrab.grab(bbox=frame_rect) if full else stat_reader.grab(frame_rect)
        if frame is None:
            values.player_hp = values.player_mp = values.player_name = None
        else:
            values.player_hp, values.player_mp = stat_reader.read_frame(frame)
            values.player_name = player_finder.read_name(frame)
        timer.record("Stats", start)  # Includes its own screen grab while detection is off
        values.stats_read_id += 1  # Lets readers tell a fresh reading from one they've already seen
        self.find_player(frame if full else None, frame_rect)


    def find_player(self, frame, frame_rect):  # Stores the player's rect in screen coords
        if frame is None:
            values.player_rect = None
            return
        start = time.perf_counter()
        rect = player_finder.find_player(frame, values.player_name)
        values.player_rect = None if rect is None else (rect[0] + frame_rect[0], rect[1] + frame_rect[1], rect[2] + frame_rect[0], rect[3] + frame_rect[1])
        timer.record("Player", start)


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
