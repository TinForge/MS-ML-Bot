# Threads for detection: one grabs frames and runs the model, as fast as the GPU allows; a second reads
# the rest from each finished frame (HP/MP, name, minimap, the player's nametag, the map recorder) while the next one is inferred

from gui import window
import time
import threading

from data import config, values
from process import kills
from tools import quickslot, stat_reader, player_finder, minimap, minimap_mosaic, map_recorder, screen, timer

stats_interval = config.stats_interval  # Seconds between reads while detection is off and the player box is hidden
player_interval = config.player_interval  # Same, while the player box is shown


class DetectionThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)  # execute the base constructor
        global instance
        instance = self
        self.is_running = False
        self.model = None  # Loaded the first time detection runs, as importing torch and Ultralytics takes seconds
        self.last_stats_time = 0
        self.last_nametag = None  # Where the player's nametag was last found, in game area coords
        self.last_minimap = None  # Where the minimap's title was last found, in game area coords
        self.minimap_tracker = minimap_mosaic.Tracker()  # Stitches the scrolling minimap, saved per map in maps/
        self.mapper = map_recorder.Mapper()  # Follows the player on the map and records platforms, saved per map in maps/
        values.mapper = self.mapper
        self.frame_ready = threading.Condition()  # Hands each finished frame to the stats thread
        self.pending = None  # (frame, frame_rect, mobs, frame_time) waiting for the stats thread; a newer frame replaces it, so it never queues up
        self.stats_lock = threading.Lock()  # read_stats runs on one thread at a time (both threads use it while detection turns off)

    def run(self):
        stats = threading.Thread(target=self.stats_loop, name="Stats", daemon=True)
        stats.start()
        last_start = None
        while window.instance is not None:
            if self.is_running is False:
                last_start = None
                time.sleep(0.01)  # The stats thread reads HP/MP and the rest on its own meanwhile
            elif self.model is None:
                self.load_model()
            else:  # No pause: inference waits on the GPU, which lets the other threads run
                frame_start = time.perf_counter()
                if last_start is not None:
                    timer.record("Detection loop", last_start)  # Start to start, for frames per second
                last_start = frame_start
                detections = self.model.run(True, False)
                values.detected_instances = detections
                timer.record("Detection", frame_start)  # Total: grab and inference
                with self.frame_ready:  # The rest of the frame's reading happens on the stats thread
                    self.pending = (self.model.last_frame, self.model.last_frame_rect, [r for r in detections if r.name == "Mob"],
                                    self.model.last_frame_time)
                    self.frame_ready.notify()
        stats.join(timeout=1)
        self.minimap_tracker.save()  # Keep what was seen and recorded on the current map
        self.mapper.save()

    def stats_loop(self):  # Reads each finished frame; with detection off, grabs its own at a slower rate
        while window.instance is not None:
            with self.frame_ready:
                if self.pending is None:
                    self.frame_ready.wait(timeout=0.01)
                job, self.pending = self.pending, None
            if job is not None:
                start = time.perf_counter()
                self.read_stats(*job)
                timer.record("Stats frame", start)  # Total: HP/MP, player find, minimap and mapping
            elif self.is_running is False:
                self.read_stats(None, None)


    def load_model(self):
        try:
            from yolo11 import model  # Imported here so the app starts without torch
            self.model = model.Model()
        except Exception as e:
            print("Failed to load the detection model:", e)
            self.is_running = False


    def read_stats(self, frame, frame_rect, mobs=None, frame_time=None):  # Reuses the inference frame when there is one, otherwise grabs
        # at a slower rate. mobs: that frame's detected mobs, for learning where they go; frame_time: when it was grabbed
        with self.stats_lock:
            self.read_stats_now(frame, frame_rect, mobs, frame_time)

    def read_stats_now(self, frame, frame_rect, mobs, frame_time=None):
        if frame is None:
            full = values.show_player_rect or values.record_platforms or values.erase_platforms or values.show_platforms or values.show_attack_range  # Only search for the player when it's needed
            if time.time() - self.last_stats_time < (player_interval if full else stats_interval):  # Faster while the player box needs to follow smoothly
                return
            frame_rect = values.window_rect
        else:
            full = True
        self.last_stats_time = time.time()
        start = time.perf_counter()
        if frame is None and frame_rect is not None:
            frame_time = time.time()
            frame = screen.grab(frame_rect)  # Whole game area: the stats are at the bottom, the minimap at the top
            timer.record("Stats grab", start)
        # Movement needs the player soonest, so it comes first (with the name read on the last pass, which doesn't change), then
        # mapping (with the last pass's minimap, which moves slowly); HP/MP and the minimap barely change from frame to frame
        self.find_player(frame if full else None, frame_rect)
        values.player_read_id += 1  # Calculations plan again on a new position
        self.update_mapper(frame, frame_rect, mobs, frame_time)
        start = time.perf_counter()
        if frame is None:
            values.player_hp = values.player_mp = values.player_exp = values.player_name = values.minimap = values.quickslot = None
        else:
            values.player_hp, values.player_mp, values.player_exp = stat_reader.read_frame(frame)
            values.quickslot = quickslot.read_frame(frame)
            kills.instance.read(values.player_exp[0] if values.player_exp is not None else None, frame_time or time.time())
            values.player_name = player_finder.read_name(frame)
        timer.record("Stats", start)
        values.stats_read_id += 1  # Lets auto potion tell a fresh HP/MP reading from one it has already seen
        self.read_minimap(frame, frame_rect)


    def update_mapper(self, frame, frame_rect, mobs=None, frame_time=None):  # Follows the player for recording or drawing platforms, and
        # learns where mobs go. frame_time: when the frame was grabbed, which movement and the overlay's drawing ahead are timed from
        if frame is None or not (values.record_platforms or values.erase_platforms or values.show_platforms or values.calculations_active):  # Navigation uses the recorded platforms
            return
        start = time.perf_counter()
        self.mapper.update(frame, frame_rect, values.player_rect, values.minimap, frame_time or time.time(), values.record_platforms, mobs,
                           values.erase_platforms)
        timer.record("Mapping", start)


    def read_minimap(self, frame, frame_rect):  # Stores the minimap with its map area in screen coords
        if frame is None:
            return
        start = time.perf_counter()
        result, self.last_minimap = minimap.read(frame, self.last_minimap)
        if result is not None:
            x1, y1, x2, y2 = result.map_rect
            result.map_rect = (x1 + frame_rect[0], y1 + frame_rect[1], x2 + frame_rect[0], y2 + frame_rect[1])
            self.minimap_tracker.update(result, restart_ok=not self.mapper.recorded(result.map_id))
        values.minimap = result
        timer.record("Minimap", start)


    def find_player(self, frame, frame_rect):  # Stores the player's rect in screen coords
        if frame is None:
            values.player_rect = None
            return
        start = time.perf_counter()
        self.last_nametag = player_finder.find_nametag(frame, values.player_name, self.last_nametag)
        if self.last_nametag is None:
            values.player_rect = None
        else:
            rect = player_finder.character_rect(self.last_nametag, values.player_name)
            values.player_rect = (rect[0] + frame_rect[0], rect[1] + frame_rect[1], rect[2] + frame_rect[0], rect[3] + frame_rect[1])
        timer.record("Player", start)


instance: DetectionThread = None
