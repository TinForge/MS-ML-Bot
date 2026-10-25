# Tracks how far the game's camera has scrolled, from how the foreground moved between frames

import cv2
import numpy as np

region = (0.2, 0.1, 0.8, 0.84)  # Part of the game area used (x1, y1, x2, y2 as fractions), away from the minimap, quest helper, chat and status bar
scale = 0.5  # Frames are compared at half size, which is faster and still precise to about a pixel
min_response = 0.08  # Below this, the shift is too uncertain to trust (e.g. the view changed completely)


class CameraTracker:
    def __init__(self):
        self.previous = None  # Last frame's region, grey and shrunk
        self.window = None  # Hanning window, which softens the region's edges so they don't dominate the match
        self.position = (0.0, 0.0)  # How far the camera has scrolled since tracking started, in game pixels
        self.lost = False  # The last shift couldn't be measured, so position may have jumped

    def reset(self):
        self.previous = None
        self.position = (0.0, 0.0)
        self.lost = False

    def update(self, frame):  # frame: PIL image of the game area; returns the camera shift in game pixels, or None
        w, h = frame.size
        x1, y1, x2, y2 = int(w * region[0]), int(h * region[1]), int(w * region[2]), int(h * region[3])
        size = (int((x2 - x1) * scale), int((y2 - y1) * scale))
        grey = np.asarray(frame.crop((x1, y1, x2, y2)).convert("L").resize(size), dtype=np.float32)
        previous, self.previous = self.previous, grey
        if previous is None or previous.shape != grey.shape:  # First frame, or the game area changed size
            self.lost = previous is not None
            return None
        if self.window is None or self.window.shape != grey.shape:
            self.window = cv2.createHanningWindow(size, cv2.CV_32F)
        (dx, dy), response = cv2.phaseCorrelate(previous, grey, self.window)
        if response < min_response:
            self.lost = True
            return None
        shift = (-dx / scale, -dy / scale)  # The scene moves the opposite way to the camera
        self.position = (self.position[0] + shift[0], self.position[1] + shift[1])
        self.lost = False
        return shift
