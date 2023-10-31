
import os


class TextFile():
    def __init__(self, file_name, default_value):
        self.file_path = './tools/persistent/' + file_name + '.txt'
        if (self.read() == ''):
            self.save(default_value)

    def read(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                return f.read()
        else:
            return ''


    def save(self, value):
        with open(self.file_path, 'w') as f:
            f.write(str(value))


window_name = TextFile('WINDOW NAME', '(Window Name)')
snap_on_start = TextFile('SNAP ON START', 'False')


def main():
    window_name.save('test')
    print(window_name.read())

    snap_on_start.save(False)
    print(snap_on_start.read())


if __name__ == "__main__":
    main()