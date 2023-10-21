# Runs GUI, Threading, and Logic together

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.page import main_page
from tools import values

from process import decision, inferencer

import multiprocessing
import threading

from yolov5 import detection


def meowwwww():

    # Run ML
    inference_done = multiprocessing.Event()
    # inference_process = inferencer.InferenceProcess(inference_done)
    # inference_process.start()  #

    inference_thread = inferencer.InferenceThread(inference_done)
    inference_thread.start()  #

    # Bot Logic
    # decision_process = decision.DecisionProcess(inference_done)
    # decision_process.start()

    decision_thread = decision.DecisionThread(inference_done)
    decision_thread.start()


    # model = detection.Model()  # #####
    while window.instance is not None:
        # model.simple_run()  # #####
        values.update()
        window.instance.refresh()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()

    # inference_process.kill()
    # decision_process.kill()
    inference_thread.kill()
    decision_thread.kill()


def main():
    window.main2()  # Initialize
    window.instance.switch_page(main_page.MainPage)  # Bootstrap into main page
    meowwwww()


if __name__ == "__main__":
    print("Launching Bootstrapper...")
    main()