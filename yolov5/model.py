# Controls the ML Inferencing Model
import torch
from PIL import ImageGrab
from tools import overlay
from data import values, rects


class Model:
    def __init__(self):
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='yolov5/weights.pt')

        if torch.cuda.is_available():
            self.model.cuda()
        else:
            self.model.cpu()

        # self.model.imgsz = 1280  # doesn't help
        self.model.conf = 0.75  # confidence threshold (0-1)
        self.model.iou = 0.5  # NMS IoU threshold (0-1)


    def run(self, crop=True, debug=True):
        detections = []
        if crop:
            im = ImageGrab.grab(bbox=values.window_rect)  # Provides rect of maplestory window, however the rects need to be localized back to window coords
        else:
            im = ImageGrab.grab()  # Data will not be as accurate if image set is not cropped

        results = self.model(im)
        labels, cord_thres = results.xyxy[0][:, -1].cpu().numpy(), results.xyxy[0][:, :-1].cpu().numpy()

        if debug:
            results.print()

        # results.save()  # saves image locally
        # print(*labels)
        # print(*cord_thres)
        # print(results.pandas().xyxy[0])  # prints each element

        for x in range(len(labels)):
            # print(labels[x])
            # print(cord_thres[x])
            if labels[x] == 0.0:  # Ground
                name = "Ground"
                color = 'brown'
            elif labels[x] == 1.0:  # Ladder
                name = "Ladder"
                color = 'yellow'
            elif labels[x] == 2.0:  # Mob
                name = "Mob"
                color = 'red'
            elif labels[x] == 3.0:  # NPC
                name = "NPC"
                color = 'purple'
            elif labels[x] == 4.0:  # Player
                name = "Player"
                color = 'blue'
            else:
                name = "Unknown"
                color = 'white'

            r = rects.Rect(name, color, cord_thres[x][0], cord_thres[x][1], cord_thres[x][2], cord_thres[x][3])
            detections.append(r)

        return detections


def main():
    i = Model()
    i.run()
    # rects = i.run()
    # print(*rects)


if __name__ == '__main__':
    main()
