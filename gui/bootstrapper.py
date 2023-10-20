from tkinter import *
from tkinter.ttk import *

from gui import window
from gui.page import main_page
from tools import values


def loop():
    while window.instance is not None:
        # Get values
        values.update()
        # Refresh GUI
        window.instance.tk.update_idletasks()
        window.instance.tk.update()
        # Run ML
        # Bot Logic


def main():
    window.instance = window.Window()
    window.instance.switch_page(main_page.MainPage)
    loop()


if __name__ == "__main__":
    print("Launching Boostrapper...")
    main()