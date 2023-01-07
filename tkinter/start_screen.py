from tkinter import *
import app


class StartPage(Frame):
    def __init__(self, frame):
        Frame.__init__(self, frame)
        Label(self, text="This is the start page").pack(side="top", fill="x", pady=10)
        Button(self, text="Open page one", command=lambda: frame.switch_frame(PageOne)).pack()
        Button(self, text="Open page two", command=lambda: frame.switch_frame(PageTwo)).pack()


class PageOne(Frame):
    def __init__(self, frame):
        Frame.__init__(self, frame)
        Label(self, text="This is page one").pack(side="top", fill="x", pady=10)
        Button(self, text="Return to start page", command=lambda: frame.switch_frame(StartPage)).pack()


class PageTwo(Frame):
    def __init__(self, frame):
        Frame.__init__(self, frame)
        Label(self, text="This is page two").pack(side="top", fill="x", pady=10)
        Button(self, text="Return to start page", command=lambda: frame.switch_frame(StartPage)).pack()


def main():
    app.initialize()
    app.instance.switch_frame(StartPage)
    app.instance.window.mainloop()



if __name__ == "__main__":
    print("Launching Start Screen...")
    main()