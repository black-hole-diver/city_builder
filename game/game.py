import pygame as pg
import sys
import random

from .world import World
from .utils import draw_text
from .camera import Camera
from .hud import Hud
from .workers import Worker
from .resource_manager import ResourceManager
from .setting import INITIAL_WORKER, BACKGROUND_COLOR, WHITE, MAP_WIDTH


class Game:
    def __init__(self, screen, clock):
        self.paused = False
        self.stars = []
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
        self.camera.scroll.x = -(MAP_WIDTH / 2 - self.width / 2)
        self.camera.scroll.y = -(MAP_WIDTH / 2 - self.width / 2)

        self.playing = False

        # Stars
        self.background = self.create_starry_background()
        self.star_offset = 0  # for slow swirl animation

    def create_starry_background(self):
        surface = pg.Surface((self.width, self.height))

        # --- Gradient sky ---
        for y in range(self.height):
            r = 10
            g = 10 + int(y * 0.05)
            b = 35 + int(y * 0.15)
            pg.draw.line(surface, (r, g, b), (0, y), (self.width, y))

        # --- Random stars ---

        for _ in range(120):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            radius = random.randint(1, 3)
            brightness = random.randint(150, 255)
            self.stars.append([x, y, radius, brightness])

        return surface

    def run(self):
        self.playing = True
        while self.playing:
            self.clock.tick(60)
            self.events()
            if not self.paused:
                self.update()
            self.draw()

    def events(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    self.quit_game()
                if event.key == pg.K_SPACE:
                    self.paused = not self.paused

    def update(self):
        self.camera.update()
        self.world.update(self.camera, self.paused)

        if not self.paused:
            # stars
            self.star_offset += .2

            # Update all active entities
            for e in self.entities:
                e.update()

            self.hud.update()


    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)

        for star in self.stars:
            x, y, radius, brightness = star

            glow_color = (brightness, brightness, 180)
            pg.draw.circle(self.screen, glow_color, (x, y), radius)

        self.world.draw(self.screen, self.camera)
        self.hud.draw(self.screen)

        if self.paused:
            draw_text(
                self.screen,
                "SYSTEM PAUSED",
                80,
                WHITE,
                (self.width // 2 - 200, self.height // 2 - 40)
            )

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