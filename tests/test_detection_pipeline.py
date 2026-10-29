# Tests for the detection pipeline: the model's thread and the stats thread working on frames side by side, with fakes for the model
# and the reading, so it runs without the game or a GPU

import threading
import time
import unittest
from unittest import mock

from data import values
from gui import window
from process import detection

INFERENCE, READING = 0.01, 0.05  # Seconds the fake model and the fake stats reading take per frame


class FakeModel:
    def __init__(self):
        self.frames = 0
        self.last_frame = self.last_frame_rect = self.last_frame_time = None

    def run(self, crop, debug):
        time.sleep(INFERENCE)
        self.frames += 1
        self.last_frame, self.last_frame_rect = self.frames, (0, 0, 100, 100)  # The frame's number stands in for its image
        return []


class PipelineTests(unittest.TestCase):
    def test_slow_reading_never_holds_up_detection(self):
        thread = detection.DetectionThread()
        thread.model, thread.is_running = FakeModel(), True
        read = []  # (thread name, frame number) of each frame the stats were read from

        def read_stats_now(frame, frame_rect, mobs, frame_time=None):
            if frame is not None:
                read.append((threading.current_thread().name, frame))
            time.sleep(READING)

        with mock.patch.object(window, "instance", object()), mock.patch.object(thread, "read_stats_now", read_stats_now), \
                mock.patch.object(thread.mapper, "save"), mock.patch.object(thread.minimap_tracker, "save"), \
                mock.patch.object(values, "detected_instances", None):
            runner = threading.Thread(target=thread.run)
            runner.start()
            time.sleep(0.5)
            window.instance = None  # Ends both loops
            runner.join(timeout=3)
        frames = thread.model.frames
        self.assertGreater(frames, 0.5 / (INFERENCE * 2))  # Detection ran at about the model's speed, not the reading's
        self.assertLess(len(read), frames)  # The stats thread skipped to the newest frame rather than queueing them all
        self.assertTrue(read and all(name == "Stats" for name, _ in read))  # On its own thread
        self.assertEqual([f for _, f in read], sorted(set(f for _, f in read)))  # Always forward, never an old frame twice


    def test_player_found_first(self):  # Movement needs the position soonest; HP/MP and the minimap barely change between frames
        thread = detection.DetectionThread()
        order = []
        ids = lambda: (values.player_read_id, values.stats_read_id)
        with mock.patch.object(thread, "find_player", lambda frame, rect: order.append(("player", ids()))), \
                mock.patch.object(thread, "update_mapper", lambda frame, rect, mobs, frame_time: order.append(("mapping", ids()))), \
                mock.patch.object(thread, "read_minimap", lambda frame, rect: order.append(("minimap", ids()))), \
                mock.patch.object(detection.stat_reader, "read_frame", lambda frame: order.append(("hp/mp", ids())) or (None, None, None)), \
                mock.patch.object(detection.player_finder, "read_name", lambda frame: None),                 mock.patch.object(detection.quickslot, "read_frame", lambda frame: None), \
                mock.patch.object(values, "player_read_id", 0), mock.patch.object(values, "stats_read_id", 0):
            thread.read_stats_now(object(), (0, 0, 100, 100), [])
        # Each signal right after its reading: calculations plan on the new position, auto potion on the new HP/MP
        self.assertEqual(order, [("player", (0, 0)), ("mapping", (1, 0)), ("hp/mp", (1, 0)), ("minimap", (1, 1))])


if __name__ == "__main__":
    unittest.main()
