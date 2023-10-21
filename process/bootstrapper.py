# Runs GUI, Threading, and Logic together

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.page import main_page
from tools import values

from process import decision, inferencer

import torch.multiprocessing as multiprocessing

from yolov5 import detection


def loop():
    model = detection.Model()  # #####

    # Run ML
    inference_done = multiprocessing.Event()
    inference_process = inferencer.InferenceProcess(inference_done, model)
    inference_process.start()  #

    # Bot Logic
    decision_process = decision.DecisionProcess(inference_done)
    decision_process.start()


    while window.instance is not None:
        # model.simple_run()  # #####
        values.update()
        window.instance.refresh()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()

    inference_process.kill()
    decision_process.kill()


def main():
    window.main2()  # Initialize
    window.instance.switch_page(main_page.MainPage)  # Bootstrap into main page
    loop()


if __name__ == "__main__":
    print("Launching Bootstrapper...")
    main()