# Fast screen capture through DXGI (dxcam), with Pillow as a fallback

import threading
import dxcam
from PIL import Image, ImageGrab

camera = None
last_frame = None  # Whole screen; dxcam only returns a frame when something changed, so this is reused otherwise
lock = threading.Lock()


def grab(bbox):  # PIL image of the screen area (x1, y1, x2, y2), like ImageGrab.grab
    global camera, last_frame
    with lock:
        if camera is None:
            camera = dxcam.create(output_color="RGB")  # Primary monitor
        frame = camera.grab()
        if frame is not None:
            last_frame = frame
        screen = last_frame
    x1, y1, x2, y2 = bbox
    if screen is None or x1 < 0 or y1 < 0 or x2 > screen.shape[1] or y2 > screen.shape[0]:  # No frame yet, or off the primary monitor
        return ImageGrab.grab(bbox=bbox, all_screens=True)
    return Image.fromarray(screen[y1:y2, x1:x2])


def grab_game(window_rect, crop=True):  # (image, rect it was grabbed from): the game area, or the whole screen with rect None
    if crop and window_rect is not None:
        return grab(window_rect), window_rect
    return ImageGrab.grab(), None  # Detections are less accurate on the whole screen
