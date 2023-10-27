# Thread for detecting models

from gui import window
import time
import threading

from data import values
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


instance: DetectionThread = None
