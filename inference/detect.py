import torch
from PIL import ImageGrab
from gui import overlay
from mapletools import values


class Inferencer:
    def __init__(self):
        self.model = torch.hub.load('ultralytics/yolov5', 'custom', path='inference/maple_weights.pt')
        self.model.cuda()
        # self.model.cpu()

    def simple_run(self):
        im = ImageGrab.grab()
        results = self.model(im)
        results.print()  # prints general info
        print(results.pandas().xyxy[0])  # prints each element


    def run(self):
        rects = []
        #
        im = ImageGrab.grab()
        # im = ImageGrab.grab(bbox=values.windowRect)  # Provides rect of maplestory window, however the rects need to be localized back to window coords
        results = self.model(im)
        # results.save()
        labels, cord_thres = results.xyxy[0][:, -1].cpu().numpy(), results.xyxy[0][:, :-1].cpu().numpy()
        results.print()
        # print(*labels)
        # print(*cord_thres)

        for x in range(len(labels)):
            # print(labels[x])
            # print(cord_thres[x])
            if labels[x] == 0.0:
                color = 'red'
            elif labels[x] == 2.0:
                color = 'blue'
            else:
                color == 'white'

            r = overlay.Rect(cord_thres[x][0], cord_thres[x][1], cord_thres[x][2], cord_thres[x][3], color)
            rects.append(r)

        return rects


def main():
    i = Inferencer()
    i.simple_run()
    # rects = i.run()
    # print(*rects)


if __name__ == '__main__':
    main()