import pygame
import overlay


# Trying to figure out running a loop for input in tandem with overlay.main_loop()
def main():
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_0:
                    instance.quit()


if __name__ == "__main__":
    instance = overlay.Overlay()
    main()
