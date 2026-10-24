# Measures how long processes take, for the Diagnostics panel

import time
from data import values

smoothing = 0.1  # Weight of the newest sample, so the numbers are readable rather than flickering
stale_time = 1.0  # Seconds without a sample before a timing counts as stopped


def record(name, start):  # start is a time.perf_counter() value taken before the work
    ms = (time.perf_counter() - start) * 1000
    old = values.timings.get(name)
    if old is not None and time.time() - old[1] < stale_time:
        ms = old[0] + (ms - old[0]) * smoothing
    values.timings[name] = (ms, time.time())


def get(name):  # Smoothed milliseconds, or None if not running
    timing = values.timings.get(name)
    if timing is None or time.time() - timing[1] >= stale_time:
        return None
    return timing[0]
