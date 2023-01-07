from tkinter import *
import window


class StartPage(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="This is the start page").pack(side="top", fill="x", pady=10)
        Button(self, text="Open page one", command=lambda: app.switch_page(PageOne)).pack()
        Button(self, text="Open page two", command=lambda: app.switch_page(PageTwo)).pack()


class PageOne(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="This is page one").pack(side="top", fill="x", pady=10)
        Button(self, text="Return to start page", command=lambda: app.switch_page(StartPage)).pack()


class PageTwo(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="This is page two").pack(side="top", fill="x", pady=10)
        Button(self, text="Return to start page", command=lambda: app.switch_page(StartPage)).pack()


def main():
    app = window.Window()
    app.switch_page(StartPage)
    app.tk.mainloop()



if __name__ == "__main__":
    print("Launching Start Screen...")
    main()