from multiprocessing import Process


# Create a new process with a specified function to execute.
def example_function():
    pass


def main():
    new_process = Process(target=example_function)

    # Run the new process
    new_process.start()

    # Check process is running
    print(new_process.is_alive())


if __name__ == '__main__':
    main()