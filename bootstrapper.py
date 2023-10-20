# Runs GUI, Threading, and Logic together

from tkinter import *
from tkinter.ttk import *

import time
import multiprocessing

from gui import window
from gui.page import main_page
from tools import values


def inference():
    while window.instance is not None:
        # time.sleep(0.1)  # Adjustable
        print('MEOW')


def logic():
    while window.instance is not None:
        # time.sleep(0.1)  # Adjustable
        print('WOOF')


def loop():
    # Run ML
    process1 = multiprocessing.Process(target=inference)
    process1.start()

    # Bot Logic
    process2 = multiprocessing.Process(target=logic)
    process2.start()

    while window.instance is not None:
        # Refresh GUI
        values.update()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()


def main():
    window.main2()  # Initialize
    window.instance.switch_page(main_page.MainPage)  # Bootstrap into main page
    loop()


if __name__ == "__main__":
    print("Launching Boostrapper...")
    main()