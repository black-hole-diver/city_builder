import pygame as pg
from game.game import Game
# import sys
# import os

# producing a .app with pyinstaller:
# `pyinstaller --noconfirm --onedir --windowed --name "Power City Builder" \
# --add-data "assets:assets" \ __main__.py``

# if getattr(sys, "frozen", False):
#     application_path = os.path.dirname(sys.executable)
# else:
#     application_path = os.path.dirname(os.path.abspath(__file__))
# os.chdir(application_path)

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
