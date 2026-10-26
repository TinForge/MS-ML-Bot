# Runs the YOLO11 mob/loot model (trained in G:\Repositories\ms-model-yolo11s) on the game area
import os
import time

import numpy as np
from ultralytics import YOLO

from tools import screen, timer
from data import config, values, rects

weights = "yolo11/weights.pt"  # Copy of ms-model-yolo11s/runs/<run>/weights/best.pt
engine = "yolo11/weights.engine"  # TensorRT build of the same model (best.engine), about twice as fast; used when it loads
COLORS = {"Mob": "red", "Loot": "cyan"}


class Model:  # run() returns this frame's detections as Rects in screen coords; last_frame is the image they came from
    def __init__(self):
        self.model = load()
        self.last_frame = None  # Last grabbed game area, None if the grab wasn't cropped to it
        self.last_frame_rect = None  # Screen rect last_frame was grabbed from

    def run(self, crop=True, debug=True):
        start = time.perf_counter()
        now = int(time.time() * 1000)  # When the frame was grabbed: detections show the game as it was then
        im, frame_rect = screen.grab_game(values.window_rect, crop)  # window_rect read once: the GUI thread keeps updating it
        offset_x, offset_y = frame_rect[:2] if frame_rect is not None else (0, 0)  # Shifts detections back to screen coords
        self.last_frame, self.last_frame_rect = (im, frame_rect) if frame_rect is not None else (None, None)
        timer.record("Grab", start)

        start = time.perf_counter()
        result = self.model.predict(im, imgsz=config.model_imgsz, conf=values.model_conf, iou=values.model_iou, verbose=False)[0]
        boxes = result.boxes
        coords, confidences, labels = boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy(), boxes.cls.cpu().numpy().astype(int)
        timer.record("Inference", start)  # After .cpu(), which waits for the GPU to finish
        if debug:
            print(result.verbose())

        detections = []
        for (x1, y1, x2, y2), confidence, label in zip(coords, confidences, labels):
            name = result.names[label]
            detections.append(rects.Rect(name, COLORS.get(name, "white"), x1 + offset_x, y1 + offset_y, x2 + offset_x, y2 + offset_y, round(float(confidence), 2), now))
        return detections


def load():  # The TensorRT engine if there is one that works on this GPU, else the PyTorch weights
    if os.path.exists(engine):
        try:
            model = YOLO(engine, task="detect")
            model.predict(np.zeros((64, 64, 3), np.uint8), imgsz=config.model_imgsz, verbose=False)  # Fails here if the engine was built for another GPU or TensorRT
            print("Detection model: TensorRT engine")
            return model
        except Exception as e:
            print("TensorRT engine didn't load, using the PyTorch weights:", e)
    print("Detection model: PyTorch weights")
    return YOLO(weights)
