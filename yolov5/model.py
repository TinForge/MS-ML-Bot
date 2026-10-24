# Controls the ML Inferencing Model
import time
import torch
from PIL import ImageGrab
from tools import overlay, screen, timer
from data import values, rects

# YOLOv5 code fetched by torch.hub, pinned to a master commit (newest tag v7.0 predates torch 2.6 support)
yolov5_repo = 'ultralytics/yolov5:af08ba156fd58ed5b0fe7e4e58a22c72c3cdd0ce'


class Model:
    def __init__(self):
        self.model = torch.hub.load(yolov5_repo, 'custom', path='yolov5/weights.pt', trust_repo=True)

        if torch.cuda.is_available():
            self.model.cuda()
        else:
            self.model.cpu()

        # self.model.imgsz = 1280  # doesn't help
        self.model.iou = values.model_iou
        self.model.conf = values.model_conf
        self.last_frame = None  # Last grabbed game area, None if the grab wasn't cropped to it
        self.last_frame_rect = None  # Screen rect last_frame was grabbed from
        # self.model.iou = 0.7  # NMS IoU threshold (0-1)        0.45 good, 0.65 good
        # self.model.conf = 0.35  # confidence threshold (0-1)     0.6 good, 0.4 good


    def run(self, crop=True, debug=True):
        detections = []
        start = time.perf_counter()
        window_rect = values.window_rect  # Read once, the GUI thread keeps updating it
        if crop and window_rect is not None:
            im = screen.grab(window_rect)  # Crop to the game client area
            offset_x, offset_y = window_rect[0], window_rect[1]  # Shifts detections back to screen coords
            self.last_frame = im
            self.last_frame_rect = window_rect
        else:
            im = ImageGrab.grab()  # Data will not be as accurate if image set is not cropped
            offset_x, offset_y = 0, 0
            self.last_frame = None
        timer.record("Grab", start)

        self.model.iou = values.model_iou
        self.model.conf = values.model_conf

        start = time.perf_counter()
        results = self.model(im)
        labels, cord_thres, confidences = results.xyxy[0][:, -1].cpu().numpy(), results.xyxy[0][:, :-1].cpu().numpy(), results.pred[0][:, :-1].cpu().numpy()
        timer.record("Inference", start)  # After .cpu(), which waits for the GPU to finish

        if debug:
            results.print()
            # print(results.pandas().xyxy[0])  # prints each element

        # results.save()  # saves image locally
        # print(*labels)
        # print(*cord_thres)

        for x in range(len(labels)):
            # print(labels[x])
            # print(cord_thres[x])
            if labels[x] == 0.0:  # Platform
                name = "Platform"
                color = 'brown'
            elif labels[x] == 1.0:  # Ladder
                name = "Ladder"
                color = 'yellow'
            elif labels[x] == 2.0:  # Mushroom
                name = "Mob"
                color = 'red'
            elif labels[x] == 3.0:  # Pig
                name = "Mob"
                color = 'red'
            elif labels[x] == 4.0:  # Player
                name = "Player"
                color = 'blue'
            elif labels[x] == 5.0:  # Slime
                name = "Mob"
                color = 'red'
            elif labels[x] == 6.0:  # Snail
                name = "Mob"
                color = 'red'
            elif labels[x] == 7.0:  # Stump
                name = "Mob"
                color = 'red'
            else:
                name = "Unknown"
                color = 'white'

            x1, y1, x2, y2 = cord_thres[x][0] + offset_x, cord_thres[x][1] + offset_y, cord_thres[x][2] + offset_x, cord_thres[x][3] + offset_y
            r = rects.Rect(name, color, x1, y1, x2, y2, round(confidences[x][4], 2), int(time.time() * 1000))
            detections.append(r)

        return detections


def main():
    i = Model()
    i.run()
    # rects = i.run()
    # print(*rects)


if __name__ == '__main__':
    main()
