# Runs GUI, Threading, and Logic together

from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.page import main_page
from tools import values

from process import decision, detection


def run():
    # Run ML
    detection_thread = detection.DetectionThread()
    detection_thread.start()

    # Bot Logic
    decision_thread = decision.DecisionThread()
    decision_thread.start()

    # GUI
    while window.instance is not None:
        values.update()
        window.instance.refresh()
        window.instance.tk.update_idletasks()
        window.instance.tk.update()


def main():
    window.main(True)  # Initialize
    window.instance.switch_page(main_page.MainPage)  # Bootstrap into main page
    run()


if __name__ == "__main__":
    print("Launching Bootstrapper...")
    main()