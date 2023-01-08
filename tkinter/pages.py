from tkinter import *
from tkinter.ttk import *
import PIL.Image
import PIL.ImageTk
import window
import references


class StartPage(Frame):
    def __init__(self, app: window.Window):
        app.tk.geometry("300x450")
        Frame.__init__(self, app.tk)
        Label(self, text="Welcome to Maplestory ML Bot", font='bold').pack(side="top", pady=20)
        Button(self, text="Launch", command=lambda: app.switch_page(MainPage)).pack()
        self.photo = PIL.ImageTk.PhotoImage(PIL.Image.open(references.mushroom_image))
        Label(self, image=self.photo).pack(fill=BOTH)
        Label(self, text="V0.1 - 08/01/2023").pack(side="top", pady=10)
        Label(self, text="Developed by Wei").pack(side="top", pady=10)


class MainPage(Frame):
    def __init__(self, app: window.Window):
        app.tk.geometry("300x500")
        Frame.__init__(self, app.tk)
        Label(self, text="Main Page").pack(side="top", pady=10)
        Button(self, text="Return to start page", command=lambda: app.switch_page(StartPage)).pack()

        Button(self, text="Open page one", command=lambda: app.switch_page(PageOne)).pack()
        Button(self, text="Open page two", command=lambda: app.switch_page(PageTwo)).pack()


        # # status group
        # status_group = gp.LabelContainer(app, "Status")
        # status_group.set_grid(1, 2)
        # status_group.set_column_weights(0, 0)

        # # elements
        # element1 = gp.Label(status_group, "Maplestory Found:")
        # status_group.add(element1, 1, 1, align="center")
        # self.app_found = gp.Label(status_group, "-/-")
        # status_group.add(self.app_found, 1, 2, align="center")



class PageOne(Frame):
    def __init__(self, app: window.Window):
        Frame.__init__(self, app.tk)
        Label(self, text="This is page one").pack(side="top", pady=10)
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