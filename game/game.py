import pygame as pg
import sys

from .world import World
from .utils import draw_text
from .camera import Camera
from .hud import Hud
from .workers import Worker
from .resource_manager import ResourceManager
from .setting import INITIAL_WORKER

class Game:
    def __init__(self, screen, clock):
        self.screen = screen
        self.clock = clock
        self.width, self.height = screen.get_size()

        # Shared list for all active game entities
        self.entities = []

        # Resource manager
        self.resource_manager = ResourceManager()

        self.hud = Hud(self.resource_manager,self.width, self.height)
        self.world = World(self.resource_manager, self.entities, self.hud, 50, 50, self.width, self.height)
        for _ in range(INITIAL_WORKER): Worker(self.world.world[25][25], self.world)
        self.camera = Camera(self.width, self.height)

        self.playing = False

    def run(self):
        self.playing = True
        while self.playing:
            self.clock.tick(60)
            self.events()
            self.update()
            self.draw()

    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.quit_game()

    def update(self):
        self.camera.update()

        # Update all active entities
        for e in self.entities:
            e.update()

        self.hud.update()
        self.world.update(self.camera)

    def draw(self):
        self.screen.fill((0, 0, 0))

        self.world.draw(self.screen, self.camera)
        self.hud.draw(self.screen)

        # Updated to use a modern Python f-string
        draw_text(
            self.screen,
            f"FPS: {int(self.clock.get_fps())}",
            25,
            (255, 255, 255),
            (10, 10)
        )

        pg.display.flip()

    def quit_game(self):
        """Helper method to handle clean exits."""
        self.playing = False
        pg.quit()
        sys.exit()