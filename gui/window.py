from tkinter import Tk, PhotoImage
import sv_ttk  # Windows 11 type theme
from gui import references


class Window:
    def __init__(self):
        self.tk: Tk = Tk()
        self.width = self.tk.winfo_screenwidth()
        self.height = self.tk.winfo_screenheight()
        self.active_page = None
        self.tk.title("Maplestory ML Bot")
        self.tk.resizable(False, False)
        self.tk.eval('tk::PlaceWindow . center')  # Centers it in screen
        icon = PhotoImage(file=references.app_icon)
        self.tk.wm_iconphoto(False, icon)
        sv_ttk.set_theme("light")


    def switch_page(self, page_class):
        if self.active_page is not None:
            self.active_page.destroy()
        self.active_page = page_class(self)
        self.active_page.pack()


instance: Window = None


def main():
    global instance
    instance = Window()
    instance.tk.mainloop()


if __name__ == "__main__":
    print("Initializing app...")
    main()
