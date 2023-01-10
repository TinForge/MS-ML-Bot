from tkinter import *
from tkinter.ttk import *
import PIL.Image
import PIL.ImageTk
import window
import mainpage
import references


class StartPage(Frame):
    def __init__(self, app: window.Window):
        app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        Label(self, text="Welcome to Maplestory ML Bot", font='bold').pack(pady=20)
        Button(self, text="Launch", command=lambda: app.switch_page(mainpage.MainPage)).pack()
        self.photo = PIL.ImageTk.PhotoImage(PIL.Image.open(references.mushroom_image))
        Label(self, image=self.photo).pack(fill=BOTH, anchor="center")
        Label(self, text="V0.1 - 08/01/2023").pack(pady=10)
        Label(self, text="Developed by Wei").pack(pady=10)


class PageOne(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="This is page one").pack(pady=10)
        Button(self, text="Return to start page", command=lambda: app.switch_page(StartPage)).pack()


class PageTwo(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="This is page two").pack(fill="x", pady=10)
        Button(self, text="Return to start page", command=lambda: app.switch_page(StartPage)).pack()


def main():
    window.instance = window.Window()
    window.instance.switch_page(StartPage)
    window.instance.tk.mainloop()


if __name__ == "__main__":
    print("Launching Start Page...")
    main()