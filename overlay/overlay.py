import sys
import pygame
import win32api
import win32con
import win32gui
import settings


class Overlay:

    def __init__(self):
        print("Launching overlay window...")

        # initialization
        pygame.init()
        pygame.display.set_caption(settings.window_name)

        self.clock = pygame.time.Clock()
        self.screen = pygame.display.set_mode((0, 0))

        # window settings
        hwnd = pygame.display.get_wm_info()["window"]
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*settings.clear_background_color), 0, win32con.LWA_COLORKEY)
        self.main_loop()


    def set_rects(self):
        self.rects = [(100, 25), (200, 50), (300, 75)]


    def main_loop(self):
        # event listener to quit screen
        def check_quit():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

        # iterating block
        while True:
            check_quit()

            # set window to transparent
            self.screen.fill(settings.clear_background_color)

            self.set_rects()

            # drawing Rectangle
            for x, y in self.rects:
                pygame.draw.rect(self.screen, settings.bounding_box_color, pygame.Rect(x + self.clock.get_time(), y, 50, 50), settings.bounding_box_thickness)

            # pygame.display.flip()
            pygame.display.update()

            # refresh at X frames per second
            self.clock.tick(settings.window_framerate)


if __name__ == "__main__":
    Overlay()
