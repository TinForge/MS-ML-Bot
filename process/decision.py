from gui import window
import time
import threading


class DecisionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor

        global instance
        instance = self

        self.is_running = False


    def run(self):
        while window.instance is not None:
            if self.is_running is False:
                time.sleep(0.1)  # Adjustable
            else:
                time.sleep(0.1)


instance: DecisionThread = None