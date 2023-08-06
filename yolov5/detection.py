import torch
from PIL import ImageGrab
from gui import overlay
from mapletools import values
import threading


class Model:
    def __init__(self):
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5/weights.pt')
        self.model.cuda()
        # self.model.cpu()
        self.model.conf = 0.75  # confidence threshold (0-1)
        self.model.iou = 0.5  # NMS IoU threshold (0-1)
        # self.model.imgsz = 1280  # doesn't help

    def simple_run(self):
        im = ImageGrab.grab()  # Data will not be as accurate if image set is not cropped
        results = self.model(im)
        results.print()  # prints general info
        print(results.pandas().xyxy[0])  # prints each element
        # results.save()

    def run(self):
        rects = []
        # im = ImageGrab.grab()
        im = ImageGrab.grab(bbox=values.windowRect)  # Provides rect of maplestory window, however the rects need to be localized back to window coords
        results = self.model(im)
        labels, cord_thres = results.xyxy[0][:, -1].cpu().numpy(), results.xyxy[0][:, :-1].cpu().numpy()
        results.print()
        # print(*labels)
        # print(*cord_thres)

        for x in range(len(labels)):
            # print(labels[x])
            # print(cord_thres[x])
            if labels[x] == 0.0:  # Ground
                color = 'brown'
                # continue
            elif labels[x] == 1.0:  # Ladder
                color = 'yellow'
                # continue
            elif labels[x] == 2.0:  # Mob
                color = 'red'
            elif labels[x] == 3.0:  # NPC
                color = 'purple'
            elif labels[x] == 4.0:  # Player
                color = 'blue'
            else:
                color = 'white'

            r = overlay.Rect(cord_thres[x][0], cord_thres[x][1], cord_thres[x][2], cord_thres[x][3], color)
            rects.append(r)

        self.is_thread_running = False
        return rects

    is_thread_running = False

    def threaded_run(self):
        if not self.is_thread_running:
            self.is_thread_running = True
            thread_inference = threading.Thread(target=self.run)
            thread_inference.start()


def main():
    i = Model()
    i.simple_run()
    # rects = i.run()
    # print(*rects)


if __name__ == '__main__':
    main()
