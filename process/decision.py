import multiprocessing
import time
import threading


class DecisionProcess(multiprocessing.Process):
    def __init__(self, inference_done):
        multiprocessing.Process.__init__(self)  # execute the base constructor
        self.data = multiprocessing.Value('i', 0)
        self.inference_done = inference_done

    def run(self):
        while True:
            self.inference_done.wait()
            self.inference_done.clear()
            time.sleep(0.1)
            print("Performed Decision Process")


class DecisionThread(threading.Thread):
    def __init__(self, inference_done):
        threading.Thread.__init__(self)  # execute the base constructor
        self.data = multiprocessing.Value('i', 0)
        self.inference_done = inference_done

    def run(self):
        while True:
            self.inference_done.wait()
            self.inference_done.clear()
            time.sleep(0.1)
            print("Performed Decision Process")
