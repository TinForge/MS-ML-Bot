from tkinter import *

instance = None


class Window():
    def __init__(self):
        self.tk: Tk = Tk()
        self.active_page = None

    def switch_page(self, page_class):
        if self.active_page is not None:
            self.active_page.destroy()
        self.active_page = page_class(self)
        self.active_page.pack()


def main():
    Window()


if __name__ == "__main__":
    print("Initializing app...")
    main()