import pygame as pg
import sys
import random

from .world import World
from .utils import draw_text
from .camera import Camera
from .hud import Hud
from .workers import Worker
from .resource_manager import ResourceManager
from .setting import INITIAL_WORKER, BACKGROUND_COLOR, WHITE, MAP_WIDTH, SPEEDS

import json
import os
import datetime

class Game:
    def __init__(self, screen, clock):
        self.paused = False
        self.stars = []
        self.screen = screen
        self.clock = clock
        self.width, self.height = screen.get_size()

        self.current_date = datetime.datetime(2000,1,1)
        self.current_speed = 1
        self.day_timer = 0

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

        self.playing = False
        self.notification_text = ""
        self.notification_timer = 0

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
                if event.key == pg.K_F5:
                    self.save_game()
                if event.key == pg.K_F9:
                    self.load_game()

                if event.key == pg.K_1:
                    self.current_speed = 1
                if event.key == pg.K_2:
                    self.current_speed = 2
                if event.key == pg.K_3:
                    self.current_speed = 3

    def update(self):
        self.camera.update()
        self.world.update(self.camera, self.paused)
        self.hud.update()

        if not self.paused:
            # stars
            self.star_offset += .2

            self.day_timer += self.clock.get_time()
            if self.day_timer >= SPEEDS[self.current_speed]:
                self.current_date += datetime.timedelta(days=1)
                self.day_timer -= SPEEDS[self.current_speed]

            # Update all active entities
            for e in self.entities:
                e.update(self.current_speed)

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)

        for star in self.stars:
            x, y, radius, brightness = star

            glow_color = (brightness, brightness, 180)
            pg.draw.circle(self.screen, glow_color, (x, y), radius)

        self.world.draw(self.screen, self.camera)
        self.hud.draw(self.screen, self.current_date, self.current_speed)

        if self.paused:
            draw_text(
                self.screen,
                "SYSTEM PAUSED",
                80,
                WHITE,
                (self.width // 2 - 200, self.height // 2 - 40)
            )
        #
        # # Updated to use a modern Python f-string
        # draw_text(
        #     self.screen,
        #     f"FPS: {int(self.clock.get_fps())}",
        #     25,
        #     (255, 255, 255),
        #     (10, 10)
        # )

        if self.notification_text != "":
            if pg.time.get_ticks() - self.notification_timer < 3_000:
                color = (255,50,50) if "Found" in self.notification_text else (50,255,50)
                draw_text(
                    self.screen,
                    self.notification_text,
                    50,
                    color,
                    (self.width // 2 - 120, 30)
                )
            else:
                self.notification_text = ""

        pg.display.flip()

    def quit_game(self):
        """Helper method to handle clean exits."""
        self.playing = False
        pg.quit()
        sys.exit()

    def save_game(self, filename="savegame.json"):
        print("Saving game...")
        data = {
            "resources": self.resource_manager.resources,
            "camera": {"x": self.camera.scroll.x, "y": self.camera.scroll.y},
            "date": self.current_date.strftime("%Y-%m-%d"),
            "speed": self.current_speed,
            "map":[],
            "buildings":[],
            "workers":[]
        }
        for x in range(self.world.grid_length_x):
            row = []
            for y in range(self.world.grid_length_y):
                row.append(self.world.world[y][x]["tile"])
            data["map"].append(row)

       # 2. Save Buildings
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                b = self.world.buildings[x][y]
                if b is not None:
                    data["buildings"].append({"name": b.name, "x": x, "y": y})

        # 3. Save Workers
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                w = self.world.workers[x][y]
                if w is not None:
                    data["workers"].append({"x": x, "y": y})

        # Write to JSON
        with open(filename, "w") as f:
            json.dump(data, f)
        print("Game saved successfully!")
        self.notification_text = "Game Saved!"
        self.notification_timer = pg.time.get_ticks()

    def load_game(self, filename="savegame.json"):
        if not os.path.exists(filename):
            print("No save file found!")
            self.notification_text = "No save file found!"
            self.notification_timer = pg.time.get_ticks()
            return

        print("Loading game...")
        with open(filename, "r") as f:
            data = json.load(f)

        # 1. Restore Resources & Camera
        self.resource_manager.resources = data["resources"]
        self.camera.scroll.x = data["camera"]["x"]
        self.camera.scroll.y = data["camera"]["y"]

        saved_date = data.get("date", "2000-01-01")
        self.current_date = datetime.datetime.strptime(saved_date, "%Y-%m-%d")
        self.current_speed = data.get("speed", 1)
        self.day_timer = 0

        # 2. Clear current entities and map data
        self.entities.clear()
        self.world.buildings = [[None for _ in range(self.world.grid_length_x)] for _ in
                                range(self.world.grid_length_y)]
        self.world.workers = [[None for _ in range(self.world.grid_length_x)] for _ in
                              range(self.world.grid_length_y)]

        # 3. Restore Map Tiles
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                tile_type = data["map"][x][y]
                self.world.world[x][y]["tile"] = tile_type
                # If there's a rock or tree, there's a collision
                self.world.world[x][y]["collision"] = (tile_type != "")

        # 4. Restore Buildings
        for b_data in data["buildings"]:
            name = b_data["name"]
            x = b_data["x"]
            y = b_data["y"]

            render_pos = self.world.world[x][y]["render_pos"]
            building_class = self.world.building_types.get(name)

            if building_class:
                # Grab the correct image from the HUD dictionary
                image = self.hud.images.get(name)
                ent = building_class(render_pos, image, self.resource_manager)

                # BUG PREVENTION: The Building class automatically charges resources upon creation.
                # Since we are loading an existing game, we must refund this cost.
                for res, cost in self.resource_manager.costs.get(name, {}).items():
                    self.resource_manager.resources[res] += cost

                self.entities.append(ent)
                self.world.buildings[x][y] = ent
                self.world.world[x][y]["collision"] = True

        # 5. Restore Workers
        for w_data in data["workers"]:
            x, y = w_data["x"], w_data["y"]
            # Worker __init__ automatically appends to self.entities and self.world.workers
            Worker(self.world.world[x][y], self.world)

        # 6. Recalculate Collision Matrix for pathfinding
        self.world.collision_matrix = self.world.create_collision_matrix()

        self.notification_text = "Game Loaded!"
        self.notification_timer = pg.time.get_ticks()

        print("Game loaded successfully!")
