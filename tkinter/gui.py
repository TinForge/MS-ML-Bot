import tkinter


def main():
    window = tkinter.Tk()

    greeting = tkinter.Label(text="Hello, Tkinter")

    greeting.pack()

    window.mainloop()


if __name__ == '__main__':
    main()