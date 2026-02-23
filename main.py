import pygame as pg
from pygame.constants import FULLSCREEN
from game.game import Game

# City builder tutorial series | Pathfinding | pygame (#9)
# Arachnid 56

def main():
    running = True
    playing = True
    pg.init()
    pg.mixer.init()
    screen = pg.display.set_mode((0,0), FULLSCREEN)
    clock = pg.time.Clock()

    # implement menus


    # implement game
    game = Game(screen, clock)

    while running:
        while playing:
            game.run()

if __name__ == "__main__":
    main()