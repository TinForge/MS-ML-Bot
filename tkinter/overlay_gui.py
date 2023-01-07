import tkinter as tk
from tkinter import Canvas


class Regular:
    def __init__(self, instance: tk.Tk):
        self.instance = instance
        self.frame = tk.Frame(self.instance)
        self.button1 = tk.Button(self.frame, text='New Window', width=25, command=self.new_window)
        self.button1.pack()
        self.button1 = tk.Button(self.frame, text='Close Window', width=25, command=self.close_window)
        self.button1.pack()
        self.frame.pack()

    def new_window(self):
        self.overlay = Overlay(self.instance)


    def close_window(self):
        self.overlay.frame.destroy()


class Overlay:
    def __init__(self, instance: tk.Tk):
        self.instance = instance
        self.frame = tk.Toplevel()

        width = self.instance.winfo_screenwidth()
        height = self.instance.winfo_screenheight()

        self.frame.geometry("%dx%d" % (width, height))
        self.frame.title("Overlay")
        self.frame.attributes('-fullscreen', True)
        self.frame.config(bg='#add123')  # Makes background transparent
        self.frame.wm_attributes('-transparentcolor', '#add123')
        self.frame.wm_attributes("-topmost", True)
        self.frame.wm_attributes("-disabled", True)


        canvas = Canvas(self.frame, bg='#add123', bd=0, highlightthickness=0)
        canvas.config(width=width, height=height)  # fill screen
        # (x1,y1) top left corner and (x2, y2) bottom right corner
        canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
        canvas.create_rectangle(0, 0, 222, 155, fill='', outline='blue', width=2)
        canvas.pack()



def main():
    instance = tk.Tk()
    Regular(instance)
    instance.mainloop()



if __name__ == '__main__':
    main()