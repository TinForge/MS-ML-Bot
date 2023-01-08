from tkinter import *
import PIL.Image
import PIL.ImageTk
import window
import references


class StartPage(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="Welcome to Maplestory ML Bot").pack(side="top", pady=5)
        Label(self, text="Developed by Wei").pack(side="top", pady=5)
        self.photo = PIL.ImageTk.PhotoImage(PIL.Image.open(references.mushroom_image))
        Label(self, image=self.photo).pack()

        Button(self, text="Open page one", command=lambda: app.switch_page(PageOne)).pack()
        Button(self, text="Open page two", command=lambda: app.switch_page(PageTwo)).pack()
        app.tk.geometry("300x500")


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