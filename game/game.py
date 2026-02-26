import pygame as pg
import sys
import random

from .world import World
from .utils import draw_text
from .camera import Camera
from .hud import Hud
from .workers import Worker
from .resource_manager import ResourceManager
from .setting import *

import json
import os
import datetime

class Game:
    def __init__(self, screen, clock):
        self.menu_mouse_pressed = None
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

        self.menu_state = None
        self.save_slots = ["save_slot_1.json", "save_slot_2.json", "save_slot_3.json"]

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
                    if self.menu_state is not None:
                        self.quit_game()
                    else:
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
        if self.hud.menu_action:
            self.menu_state = self.hud.menu_action
            self.hud.menu_action = None
        if self.menu_state is not None:
            return
        self.camera.update()
        self.world.update(self.camera, self.paused)
        self.hud.update()

        if not self.paused:
            # stars
            self.star_offset += .2

            old_year = self.current_date.year
            self.day_timer += self.clock.get_time()
            if self.day_timer >= SPEEDS[self.current_speed]:
                self.current_date += datetime.timedelta(days=1)
                self.day_timer -= SPEEDS[self.current_speed]

            if self.current_date.year > old_year:
                income, expense = self.resource_manager.apply_annual_budget(self.world)
                self.notification_text += f"Yearly Budget: +${income} | -${expense}"
                self.notification_timer = pg.time.get_ticks()

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

        if self.menu_state is not None:
            self.process_menu_overlay()

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
        draw_text(
            self.screen,
            f"FPS: {int(self.clock.get_fps())}",
            25,
            (255, 255, 255),
            (10, 10)
        )

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
            "funds": self.resource_manager.funds,
            "population": self.resource_manager.population,
            "satisfaction": self.resource_manager.satisfaction,

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
                if b is not None and b.origin == (x,y):
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
        self.resource_manager.funds = data.get("funds", 20_800)
        self.resource_manager.population = data.get("population", 0)
        self.resource_manager.satisfaction = data.get("satisfaction", 100)

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
                image = self.hud.images.get(name)
                ent = building_class(render_pos, image, self.resource_manager, (x,y))

                # BUG PREVENTION: The Building class automatically charges resources upon creation.
                # Since we are loading an existing game, we must refund this cost.
                refund_amount = self.resource_manager.costs.get(name, 0)
                self.resource_manager.funds += refund_amount

                self.entities.append(ent)
                b_w = ent.grid_width
                b_h = ent.grid_height
                for i in range(x,x+b_w):
                    for j in range(y,y+b_h):
                        self.world.buildings[i][j] = ent
                        self.world.world[i][j]["collision"] = True

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

    def delete_save(self, filename):
       if os.path.exists(filename):
           os.remove(filename)
           self.notification_text = "Save Deleted!"
           self.notification_timer = pg.time.get_ticks()

    def process_menu_overlay(self):
       # Darken the background
       overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
       overlay.fill((0, 0, 0, 150))
       self.screen.blit(overlay, (0, 0))

       # Menu Box
       menu_w, menu_h = 500, 400
       menu_x, menu_y = (self.width - menu_w) // 2, (self.height - menu_h) // 2
       menu_rect = pg.Rect(menu_x, menu_y, menu_w, menu_h)
       pg.draw.rect(self.screen, (40, 40, 60), menu_rect)
       pg.draw.rect(self.screen, (255, 255, 255), menu_rect, 3)

       title = f"{self.menu_state} GAME"
       draw_text(self.screen, title, 50, (255, 255, 255), (menu_x + 130, menu_y + 20))

       mouse_pos = pg.mouse.get_pos()
       mouse_state = pg.mouse.get_pressed()

       # Independent debouncing for the menu
       if not hasattr(self, 'menu_mouse_pressed'):
           self.menu_mouse_pressed = False

       mouse_clicked = mouse_state[0] and not self.menu_mouse_pressed
       self.menu_mouse_pressed = mouse_state[0]

       # --- NEW: Draw Close [X] Button ---
       close_rect = pg.Rect(menu_x + menu_w - 40, menu_y + 10, 30, 30)
       c_color = (255, 80, 80) if close_rect.collidepoint(mouse_pos) else (200, 50, 50)
       pg.draw.rect(self.screen, c_color, close_rect)
       pg.draw.rect(self.screen, (255, 255, 255), close_rect, 2)
       draw_text(self.screen, "X", 30, (255, 255, 255), (close_rect.x + 8, close_rect.y + 6))

       # Draw the 3 slots
       for i, filename in enumerate(self.save_slots):
           slot_y = menu_y + 100 + (i * 80)
           slot_rect = pg.Rect(menu_x + 50, slot_y, 300, 60)
           reset_rect = pg.Rect(menu_x + 370, slot_y, 80, 60)

           # Peek into the file to get info
           info_text = "Empty Slot"
           if os.path.exists(filename):
               try:
                   with open(filename, "r") as f:
                       data = json.load(f)
                   if isinstance(data, dict):
                       info_text = f"Day: {data.get('date', 'Unknown')}"
                   else: info_text = "Corrupt Save"
               except json.JSONDecodeError:
                   info_text = "Corrupt JSON Save"
               except OSError:
                   info_text = "Unreadable Save"

           # Draw Slot Button
           color = (80, 80, 100) if slot_rect.collidepoint(mouse_pos) else (60, 60, 80)
           pg.draw.rect(self.screen, color, slot_rect)
           pg.draw.rect(self.screen, (255, 255, 255), slot_rect, 2)
           draw_text(self.screen, f"Slot {i + 1}: {info_text}", 25, (255, 255, 255),
                     (slot_rect.x + 10, slot_rect.y + 20))

           # Draw Reset Button
           r_color = (200, 50, 50) if reset_rect.collidepoint(mouse_pos) else (150, 40, 40)
           pg.draw.rect(self.screen, r_color, reset_rect)
           pg.draw.rect(self.screen, (255, 255, 255), reset_rect, 2)
           draw_text(self.screen, "RESET", 25, (255, 255, 255), (reset_rect.x + 10, reset_rect.y + 20))

           # Handle Clicks
           if mouse_clicked:
               # --- NEW: Handle Close Button Click ---
               if close_rect.collidepoint(mouse_pos):
                   self.menu_state = None
                   self.hud.mouse_pressed = True  # Prevent clicking things behind menu
                   return  # Exit out early

               elif reset_rect.collidepoint(mouse_pos):
                   self.delete_save(filename)
               elif slot_rect.collidepoint(mouse_pos):
                   if self.menu_state == "SAVE":
                       self.save_game(filename)
                   elif self.menu_state == "LOAD":
                       if info_text != "Empty Slot":
                           self.load_game(filename)

                   self.menu_state = None  # Close menu after action
                   self.hud.mouse_pressed = True  # Prevent clicking things behind menu when returning

       # Right-click to close
       if mouse_state[2]:
           self.menu_state = None
           self.hud.mouse_pressed = True