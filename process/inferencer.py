import multiprocessing
import ctypes
import time

from yolov5 import detection


class Result(ctypes.Structure):
    _fields_ = [('class', ctypes.c_char_p), ('color', ctypes.c_char_p), ('x1', ctypes.c_int), ('y1', ctypes.c_int), ('x2', ctypes.c_int), ('y2', ctypes.c_int)]


test_rects = [Result(b"ID1", b"green", 100, 100, 200, 200), Result(b"ID2", b"red", 300, 300, 400, 400), Result(b"ID3", b"purple", 500, 500, 600, 600)]  # The b"" encodes it as bytes


class InferenceProcess(multiprocessing.Process):
    def __init__(self, inference_done):
        multiprocessing.Process.__init__(self)  # execute the base constructor
        self.data = multiprocessing.Array(Result, [test_rects[0], test_rects[1], test_rects[2]])
        self.inference_done = inference_done
        self.model = detection.Model()  # ######

    def run(self):
        while True:
            time.sleep(1)  # Adjustable
            self.model.simple_run()  # ######
            self.inference_done.set()
