import tkinter as tk
from tkinter import Canvas


def main():
    root = tk.Tk()

    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()

    root.title("main")
    root.geometry("200x300")

    rLabel = tk.Label(root, text="This is root window")
    rLabel.pack()

    top = tk.Toplevel()
    top.geometry("%dx%d" % (width, height))
    top.title("toplevel")
    top.attributes('-fullscreen', True)
    # top.attributes('-alpha', 0.5)
    # top.lift() Not required when using topmost
    top.config(bg='#add123')  # Makes background transparent
    top.wm_attributes('-transparentcolor', '#add123')
    top.wm_attributes("-topmost", True)
    top.wm_attributes("-disabled", True)

    # tLabel = tk.Label(top, text="This is toplevel window")
    # tLabel.pack()

    canvas = Canvas(top, bg='#add123', bd=0, highlightthickness=0)
    canvas.config(width=width, height=height)  # fill screen
    # (x1,y1) top left corner and (x2, y2) bottom right corner
    canvas.create_rectangle(50, 110, 300, 280, fill='', outline='red', width=2)
    canvas.create_rectangle(0, 0, 222, 155, fill='', outline='blue', width=2)
    canvas.pack()
    # canvas.pack(fill=tk.BOTH)
    root.mainloop()



if __name__ == '__main__':
    main()