from tkinter import *

instance = None


class App():
    def __init__(self):
        self.window = Tk()
        self.current_frame = None

    def switch_frame(self, frame_class):
        new_frame = frame_class(self)
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame
        self.current_frame.pack()



def initialize():
    global instance
    if instance is None:
        instance = App()
    else:
        print("instance already exists")


def main():
    initialize()


if __name__ == "__main__":
    print("Initializing app...")
    main()