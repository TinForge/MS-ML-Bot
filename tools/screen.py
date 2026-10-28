# Fast screen capture through DXGI (dxcam), with Pillow as a fallback. Frames are H x W x 3 RGB arrays: every reader slices the bit
# it needs out of one, without copying (a PIL image cost ~2.7 ms to make, and each reader turned it back into an array anyway)

import threading
import dxcam
import numpy as np
from PIL import ImageGrab

camera = None
last = {}  # Area (x1, y1, x2, y2): its last grab. dxcam only returns a frame when something changed, so this is reused otherwise
lock = threading.Lock()


def grab(bbox):  # The screen area (x1, y1, x2, y2) as an RGB array. dxcam copies out only that area (half the work of the whole
    # screen); readers only read it, so a repeat of an unchanged frame is the same array
    global camera
    bbox = tuple(int(v) for v in bbox)
    with lock:
        if camera is None:
            camera = dxcam.create(output_color="RGB")  # Primary monitor
        x1, y1, x2, y2 = bbox
        if 0 <= x1 < x2 <= camera.width and 0 <= y1 < y2 <= camera.height:
            frame = camera.grab(region=bbox)
            if frame is not None:
                last[bbox] = frame
            if bbox in last:
                return last[bbox]
    return np.asarray(ImageGrab.grab(bbox=bbox, all_screens=True).convert("RGB"))  # Off the primary monitor, or no frame yet


def grab_game(window_rect, crop=True):  # (frame, rect it was grabbed from): the game area, or the whole screen with rect None
    if crop and window_rect is not None:
        return grab(window_rect), window_rect
    return np.asarray(ImageGrab.grab().convert("RGB")), None  # Detections are less accurate on the whole screen


def pixels(im):  # An RGB array of a frame: arrays as they are, PIL images converted (tests and tools pass those)
    return im if isinstance(im, np.ndarray) else np.asarray(im.convert("RGB"))
