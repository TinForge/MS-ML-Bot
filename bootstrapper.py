# Runs GUI, Threading, and Logic together

from tkinter import *
from tkinter.ttk import *

import time
import multiprocessing

from gui import window
from gui.page import main_page
from tools import values


def inference():
    global run_flag
    while run_flag is True:
        # time.sleep(0.1)  # Adjustable
        pass


def logic():
    global run_flag
    while run_flag is True:
        # time.sleep(0.1)  # Adjustable
        pass


def refresh():
    print("PRINTING")
    global run_flag
    while run_flag is True:
        print("PRINTING1111")
        time.sleep(0.01)  # Adjustable
        values.update()
        window.instance.refresh()


def loop():
    global run_flag
    run_flag = True

    # Run ML
    process1 = multiprocessing.Process(target=inference)
    process1.start()

    # Bot Logic
    process2 = multiprocessing.Process(target=logic)
    process2.start()

    # Refresh GUI
    process3 = multiprocessing.Process(target=refresh)
    process3.start()

    while window.instance is not None:
        time.sleep(0.1)  # Adjustable
        window.instance.tk.update_idletasks()
        window.instance.tk.update()

    run_flag = False


def main():
    window.main2()  # Initialize
    window.instance.switch_page(main_page.MainPage)  # Bootstrap into main page
    loop()


if __name__ == "__main__":
    print("Launching Bootstrapper...")
    main()