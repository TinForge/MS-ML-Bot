from gui import window
import time
import threading

from tools import values
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
                time.sleep(0.1)  # Adjustable
            else:
                print("running detect")
                time.sleep(0.1)  # Adjustable
                detections = self.model.run(True, False)
                values.detections = detections


instance: DetectionThread = None
