import pygame as pg
from pygame.constants import FULLSCREEN
from game.game import Game

# City builder tutorial series | A*Pathfinding | pygame
# Skeleton from Arachnid56

def main():
    running = True
    playing = True
    pg.init()
    pg.mixer.init()
    window_width = 1280
    window_height = 720
    screen = pg.display.set_mode((window_width, window_height), pg.RESIZABLE)
    pg.display.set_caption("City Builder")
    clock = pg.time.Clock()
    game = Game(screen, clock)

    while running:
        while playing:
            game.run()

if __name__ == "__main__":
    main()