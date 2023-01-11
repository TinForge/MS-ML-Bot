from multiprocessing import Process
import time


def do_something():
    print("I'm going to sleep")
    time.sleep(1)
    print("I'm awake")


def main():
    new_process_1 = Process(target=do_something)
    new_process_2 = Process(target=do_something)

    # Starts both processes
    new_process_1.start()
    new_process_2.start()

    new_process_1.join()
    new_process_2.join()


if __name__ == '__main__':
    main()