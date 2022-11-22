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
        self.update_loop()

    # called externally
    def set_rects(self):
        self.rects = [(100, 25), (200, 50), (300, 75)]

    # quit
    def quit(self):
        pygame.quit()
        sys.exit()

    # update loop
    def update_loop(self):
        # event listener to quit screen
        def check_quit():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.quit()

        # iterating block
        while True:
            check_quit()

            # set window to transparent
            self.screen.fill(settings.clear_background_color)

            # drawing Rectangle
            self.set_rects()

            for x, y in self.rects:
                pygame.draw.rect(self.screen, settings.bounding_box_color, pygame.Rect(x, y, 50, 50), settings.bounding_box_thickness)

            # pygame.display.flip()
            pygame.display.update()

            # refresh at X frames per second
            self.clock.tick(settings.window_framerate)


if __name__ == "__main__":
    Overlay()
