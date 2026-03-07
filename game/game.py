import pygame as pg
import sys
import random

from .systems.population_system import PopulationSystem
from .systems.power_system import PowerSystem
from .systems.economy_system import EconomySystem
from .systems.disaster_system import DisasterSystem
from .systems.construction_manager import ConstructionManager
from .systems.resource_manager import ResourceManager

from .world import World
from .utils import draw_text, logger
from .camera import Camera
from .hud import Hud
from .workers import Worker
from .buildings import ResZone, IndZone, SerZone, PowerPlant, Tree
from .event_bus import EventBus
from .setting import (
    SPEEDS,
    INITIAL_WORKER,
    MAP_WIDTH,
    MAP_HEIGHT,
    WHITE,
    BACKGROUND_COLOR,
    EntityType,
    GameEvent,
    MusicEvent,
)

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

        self.current_date = datetime.datetime(2000, 1, 1)
        self.current_speed = 1
        self.day_timer = 0

        # ============ Core Game Components ============
        self.entities = []  # Shared list for all active game entities
        self.resource_manager = ResourceManager()

        # Initialize HUD and world
        self.hud = Hud(self.resource_manager, self.width, self.height)
        # self.hud.game = self  # Give HUD a reference to game
        self.world = World(
            self, self.resource_manager, self.entities, self.hud, 50, 50, self.width, self.height
        )
        self._spawn_workers()

        # ============ Camera Setup ============
        self.camera = Camera(self.width, self.height)
        self.camera.scroll.x = -(MAP_WIDTH / 2 - self.width / 2)
        self.camera.scroll.y = -(MAP_HEIGHT / 2 - self.height / 2)

        # ============ UI and Visual Effects ============
        self.playing = False
        self.background = self.create_starry_background()
        self.star_offset = 0  # For slow swirl animation
        self.car_spawn_timer = 0
        self.notifications = []  # List of {text, color, timer, offset_y}
        self.notification_text = ""
        self.notification_timer = 0

        # ============ Dino ============
        self.rampage_active = False
        self.rampage_timer = 0
        self.dinosaur_entity = None

        # ============ Menu and Save System ============
        self.hud.active_modal = "MAIN_MENU"
        self.save_slots = ["save_slot_1.json", "save_slot_2.json", "save_slot_3.json"]

        # ============ Demolition Tracker ==========
        self.demolish_target_pos = None
        self.demolish_stats = {}

        # ============ Audio System ============

        # Load and play background music
        self.sound_on = True
        try:
            pg.mixer.music.load(MusicEvent.BACKGROUND_MUSIC)
            pg.mixer.music.set_volume(0.1)  # Set volume to 10% (0.0 to 1.0)
            pg.mixer.music.play(-1)  # Loop indefinitely
        except Exception as e:
            logger.error(f"Error loading music: {e}")

        EventBus.subscribe(GameEvent.PLAY_SOUND, self.play_sound)
        EventBus.subscribe(GameEvent.NOTIFY, self.add_notification)
        EventBus.subscribe(GameEvent.TOGGLE_MUSIC, self.toggle_music)
        EventBus.subscribe(GameEvent.START_RAMPAGE, self.start_rampage)

        # Systems
        self.power_system = PowerSystem(self.world)
        self.economy_system = EconomySystem(self.world, self.resource_manager, self)
        self.population_system = PopulationSystem(self.world, self.resource_manager, self)
        self.disaster_system = DisasterSystem(self, self.world)
        self.construction_manager = ConstructionManager(self, self.world)

    def toggle_music(self) -> None:
        self.sound_on = not self.sound_on
        if self.sound_on:
            pg.mixer.music.unpause()
            self.add_notification("SOUND: ON", (100, 255, 100))
        else:
            pg.mixer.music.pause()
            self.add_notification("SOUND: OFF", (255, 100, 100))

    def play_sound(self, sound_file_name: str) -> None:
        if self.sound_on:
            pg.mixer.Sound(sound_file_name).play()

    def create_starry_background(self) -> None:
        """Create animated starry background with gradient sky."""
        surface = pg.Surface((self.width, self.height))

        # Generate gradient sky
        for y in range(self.height):
            r = 10
            g = 10 + int(y * 0.05)
            b = 35 + int(y * 0.15)
            pg.draw.line(surface, (r, g, b), (0, y), (self.width, y))

        # Generate random stars
        for _ in range(120):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            radius = random.randint(1, 3)
            brightness = random.randint(150, 255)
            self.stars.append([x, y, radius, brightness])

        return surface

    def run(self) -> None:
        self.playing = True
        while self.playing:
            self.clock.tick(60)
            self.events()
            self.update()
            self.draw()

    def events(self) -> None:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.quit_game()
            if event.type == pg.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)

                # Update HUD dimensions and reinitialize components
                self.hud.width = self.width
                self.hud.height = self.height
                self.hud.__init__(self.resource_manager, self.width, self.height)
                self.hud.game = self

                # Update camera dimensions
                self.camera.width = self.width
                self.camera.height = self.height

                # Regenerate background to match new size
                self.background = self.create_starry_background()
            if event.type == pg.KEYDOWN:
                # Rename building
                if self.hud.active_modal == "RENAME":
                    if event.key == pg.K_RETURN:
                        if self.hud.rename_target:
                            clean_name = self.hud.rename_input_text.strip()
                            self.hud.rename_target.custom_name = clean_name if clean_name else None
                        self.hud.active_modal = None
                        self.hud.rename_input_text = ""
                    elif event.key == pg.K_ESCAPE:
                        self.hud.active_modal = None
                        self.hud.rename_input_text = ""
                    elif event.key == pg.K_BACKSPACE:
                        self.hud.rename_input_text = self.hud.rename_input_text[:-1]
                    else:
                        if len(self.hud.rename_input_text) < 18:
                            self.hud.rename_input_text += event.unicode
                            logger.info(f"Renaming building: {self.hud.rename_input_text}")
                    continue
                if event.key == pg.K_ESCAPE:
                    if self.hud.show_help:
                        self.hud.show_help = False
                    elif self.hud.show_budget:
                        self.hud.show_budget = False
                    elif self.hud.active_modal is not None:
                        self.hud.active_modal = None
                    else:
                        self.quit_game()
                if event.key == pg.K_SPACE:
                    self.paused = not self.paused
                if event.key == pg.K_F5:
                    self.hud.active_modal = "SAVE"
                if event.key == pg.K_F9:
                    self.hud.active_modal = "LOAD"

                if event.key == pg.K_f:
                    self.disaster_system.start_random_fire()

                if event.key == pg.K_1:
                    self.day_timer = (self.day_timer / SPEEDS[self.current_speed]) * SPEEDS[1]
                    self.current_speed = 1
                    self.add_notification("GAME SPEED: 1x", (200, 255, 200))
                if event.key == pg.K_2:
                    self.day_timer = (self.day_timer / SPEEDS[self.current_speed]) * SPEEDS[2]
                    self.current_speed = 2
                    self.add_notification("GAME SPEED: 2x", (255, 255, 150))
                if event.key == pg.K_3:
                    self.day_timer = (self.day_timer / SPEEDS[self.current_speed]) * SPEEDS[3]
                    self.current_speed = 3
                    self.add_notification("GAME SPEED: 3x", (255, 150, 150))
                if event.key == pg.K_4:
                    self.day_timer = (self.day_timer / SPEEDS[self.current_speed]) * SPEEDS[4]
                    self.current_speed = 4
                    self.add_notification("GAME SPEED: 4x", (255, 100, 100))

    def add_notification(self, text: str, color: tuple[int, int, int] = WHITE) -> None:
        """Add a notification message that floats up and fades out."""
        self.notifications.append(
            {"text": text, "color": color, "timer": pg.time.get_ticks(), "offset_y": 0}
        )

    def update(self) -> None:
        """Update game state, handle menu actions, and process game logic."""
        self.hud.update()
        # ============ Handle Menu Actions ============
        if self.hud.menu_action:
            if self.hud.menu_action == "SAVE":
                self.hud.active_modal = "SAVE"
            elif self.hud.menu_action == "LOAD":
                self.hud.active_modal = "LOAD"
            elif self.hud.menu_action == "MAIN_LOAD":
                # Find the most recently modified save file
                latest_save = None
                latest_time = 0
                for slot in self.save_slots:
                    if os.path.exists(slot):
                        mtime = os.path.getmtime(slot)
                        if mtime > latest_time:
                            latest_time = mtime
                            latest_save = slot

                if latest_save:
                    self.load_game(latest_save)
                    self.hud.active_modal = None
                else:
                    self.add_notification("No save files found!", (255, 100, 100))
            elif self.hud.menu_action == "RESTART":
                self.restart_game()
            elif self.hud.menu_action == "PLAY":
                self.hud.active_modal = None  # Transition to active gameplay

            self.hud.menu_action = None

        # ============ Menu State Handling ============
        # if self.hud.active_modal == "MAIN_MENU":
        #     self.hud.draw_main_menu(self.screen, self.sound_on)
        #     return

        if self.hud.active_modal is not None:
            return

        # Game over state: HUD must still update to handle buttons
        if self.resource_manager.is_mayor_replaced:
            # self.hud.update()
            return

        # ============ Core Game Updates ============
        self.camera.update()
        self.world.update(self.camera, self.paused)

        # Handle Dinosaur Button Click
        if getattr(self.hud, "dino_action", False) and not self.rampage_active:
            self.start_rampage()
            self.hud.dino_action = False

        # Handle Dinosaur Timer
        if getattr(self, "rampage_active", False):
            if pg.time.get_ticks() - self.rampage_timer >= 28000:  # 28 seconds
                self.end_rampage()

        # ============ Game Logic (When Not Paused) ============
        if not self.paused:
            # Animate stars
            self.star_offset += 0.2

            self.disaster_system.update()

            now = pg.time.get_ticks()

            # --- Car Spawning Logic ---
            if now - self.car_spawn_timer > 2000 / self.current_speed:  # Try spawning every 2s
                self.spawn_cars()
                self.car_spawn_timer = now

            # --- Time and Budget System ---
            old_year = self.current_date.year
            self.day_timer += self.clock.get_time()
            if self.day_timer >= SPEEDS[self.current_speed]:
                self.current_date += datetime.timedelta(days=1)
                self.day_timer -= SPEEDS[self.current_speed]

                # Apply daily budget update
                self.resource_manager.apply_daily_budget(self.world)

                # --- Population Growth System ---
                # Starter city boost: higher chance if population < 10
                # Regular growth: requires high satisfaction if population >= 10
                EventBus.publish("recalculate_satisfaction_and_growth")
                if hasattr(self.resource_manager, "sync_demographics"):
                    self.resource_manager.sync_demographics()
            # --- Annual Logic Trigger ---
            if self.current_date.year > old_year:
                self.economy_system.apply_annual_logic()

            # Update all entities
            for e in self.entities:
                e.update(self.current_speed)

        # Update notifications (floating up and fading)
        now = pg.time.get_ticks()
        for n in self.notifications[:]:
            if now - n["timer"] > 2500:
                self.notifications.remove(n)
            else:
                n["offset_y"] -= 1  # Float up

    # Dinosaur rampage

    def start_rampage(self) -> None:
        """Triggers the Dinosaur Rampage event."""
        now = pg.time.get_ticks()
        if (
            getattr(self, "rampage_active", False)
            or getattr(self, "dinosaur_entity", None) is not None
        ):
            self.add_notification("THE DINOSAIR IS ALREADY HERE...", (200, 200, 200))
            pg.event.clear(pg.MOUSEBUTTONDOWN)
            return
        last_end = getattr(self, "last_rampage_end", 0)
        if now - last_end < 5000:
            self.add_notification("THE CITY IS STILL RECOVERING!", (200, 200, 200))
            pg.event.clear(pg.MOUSEBUTTONDOWN)
            return
        self.rampage_active = True
        self.rampage_timer = pg.time.get_ticks()
        self.add_notification("DINOSAUR IS COMINGGGG!!!!!!!", (255, 50, 50))

        from .workers import Dinosaur

        spawned = False
        attempts = 0
        while not spawned and attempts < 1000:
            x = random.randint(0, self.world.grid_length_x - 1)
            y = random.randint(0, self.world.grid_length_y - 1)
            if not self.world.world[x][y]["collision"]:
                self.dinosaur_entity = Dinosaur(self.world.world[x][y], self.world)
                spawned = True
            attempts += 1

        try:
            pg.mixer.music.load(MusicEvent.JURASSIC_MUSIC)
            pg.mixer.music.set_volume(0.4)
            if self.sound_on:
                pg.mixer.music.play()
        except Exception as e:
            logger.error(f"Error loading dino music: {e}")

    def end_rampage(self):
        """Concludes the Dinosaur Rampage event and calculates casualties.
        Remove the dinosaur, calculate casualties (.05-.20), and restore normal conditions."""
        self.rampage_active = False
        self.add_notification("THE DINOSAUR LEFT...", (200, 200, 200))

        if self.dinosaur_entity in self.entities:
            self.entities.remove(self.dinosaur_entity)
        self.dinosaur_entity = None

        kill_pct = random.uniform(0.05, 0.20)
        total_killed = int(self.resource_manager.population * kill_pct)

        if total_killed > 0:
            self.add_notification(f"Rampage Casualties: {total_killed} citizens", (255, 50, 50))

            # Extract victims evenly from inhabited Residential Zones
            res_zones = [
                e
                for e in self.entities
                if isinstance(e, ResZone) and getattr(e, "occupants", 0) > 0
            ]
            killed_remaining = total_killed

            while killed_remaining > 0 and res_zones:
                target = random.choice(res_zones)
                target.occupants -= 1
                killed_remaining -= 1
                if target.occupants <= 0:
                    res_zones.remove(target)

            actual_killed = total_killed - killed_remaining
            self.resource_manager.total_deaths += actual_killed

            if self.resource_manager.population > 0:
                sec_ratio = self.resource_manager.edu_secondary / self.resource_manager.population
                tert_ratio = self.resource_manager.edu_tertiary / self.resource_manager.population
                self.resource_manager.edu_secondary -= int(actual_killed * sec_ratio)
                self.resource_manager.edu_tertiary -= int(actual_killed * tert_ratio)
                self.resource_manager.edu_secondary = max(0, self.resource_manager.edu_secondary)
                self.resource_manager.edu_tertiary = max(0, self.resource_manager.edu_tertiary)
            all_res_zones = [e for e in self.entities if isinstance(e, ResZone)]
            self.resource_manager.population = sum(rz.occupants for rz in all_res_zones)
            self.resource_manager.sync_demographics()
            EventBus.publish("recalculate_satisfaction")
        pg.mixer.music.load(MusicEvent.BACKGROUND_MUSIC)
        pg.mixer.music.set_volume(0.1)
        if self.sound_on:
            pg.mixer.music.play(-1)
        self.last_rampage_end = pg.time.get_ticks()
        pg.event.clear(pg.MOUSEBUTTONDOWN)

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)

        for star in self.stars:
            x, y, radius, brightness = star

            glow_color = (brightness, brightness, 180)
            pg.draw.circle(self.screen, glow_color, (x, y), radius)

        if self.hud.active_modal == "MAIN_MENU":
            self.hud.draw_main_menu(self.screen, self.sound_on)
            pg.display.flip()
            return

        self.world.draw(self.screen, self.camera)
        self.hud.draw(self.screen, self.current_date, self.current_speed, self.sound_on)

        if self.hud.active_modal in ["SAVE", "LOAD"]:
            self.process_menu_overlay()

        if self.paused:
            draw_text(
                self.screen,
                "SYSTEM PAUSED",
                80,
                WHITE,
                (self.width // 2 - 200, self.height // 2 - 40),
            )

        # ============ Draw Notifications ============
        if self.notifications:
            now = pg.time.get_ticks()
            font = pg.font.SysFont("Trebuchet MS", 26, bold=True)
            for i, n in enumerate(self.notifications):
                elapsed = now - n["timer"]
                if elapsed < 2500:
                    # Calculate fade-out alpha
                    alpha = 255
                    if elapsed > 1500:
                        alpha = int(255 * (1 - (elapsed - 1500) / 1000))

                    text_surf = font.render(n["text"], True, n["color"])
                    tw, th = text_surf.get_size()

                    padding_x, padding_y = 40, 20
                    box_w, box_h = tw + padding_x, th + padding_y
                    toast_surf = pg.Surface((box_w, box_h), pg.SRCALPHA)
                    pg.draw.rect(
                        toast_surf, (30, 30, 35, 220), (0, 0, box_w, box_h), border_radius=10
                    )
                    pg.draw.rect(
                        toast_surf,
                        n["color"],
                        (0, 0, 8, box_h),
                        border_top_left_radius=10,
                        border_bottom_left_radius=10,
                    )
                    pg.draw.rect(
                        toast_surf, (100, 100, 110, 150), (0, 0, box_w, box_h), 2, border_radius=10
                    )
                    toast_surf.blit(text_surf, (padding_x // 2 + 5, padding_y // 2))
                    toast_surf.set_alpha(alpha)
                    pos_x = (self.width - box_w) // 2
                    pos_y = 120 + (i * (box_h + 10)) + n["offset_y"]
                    self.screen.blit(toast_surf, (pos_x, pos_y))
        pg.display.flip()

    def quit_game(self):
        """Handle clean game exit."""
        logger.info("Quitting game...")
        self.playing = False
        pg.quit()
        sys.exit()

    def restart_game(self):
        """Reinitialize the game state for a fresh start."""
        self.__init__(self.screen, self.clock)
        self.hud.active_modal = None  # Start playing immediately
        self.playing = True
        self.hud.menu_action = None  # Clear lingering menu actions

    def save_game(self, filename=None):
        """Save current game state to a JSON file."""
        if filename is None:
            filename = self.save_slots[0]
        logger.info(f"Saving game to {filename}...")
        data = {
            "funds": self.resource_manager.funds,
            "population": self.resource_manager.population,
            "edu_primary": self.resource_manager.edu_primary,
            "edu_secondary": self.resource_manager.edu_secondary,
            "edu_tertiary": self.resource_manager.edu_tertiary,
            "satisfaction": self.resource_manager.satisfaction,
            "years_negative_budget": self.resource_manager.years_negative_budget,
            "is_mayor_replaced": self.resource_manager.is_mayor_replaced,
            "tax_per_citizen": self.resource_manager.tax_per_citizen,
            "total_loan_amount": self.resource_manager.total_loan_amount,
            "budget_history": self.resource_manager.budget_history,
            "sound_on": self.sound_on,
            "eviction_penalty": getattr(self.resource_manager, "eviction_penalty", 0),
            "camera": {"x": self.camera.scroll.x, "y": self.camera.scroll.y},
            "date": self.current_date.strftime("%Y-%m-%d"),
            "speed": self.current_speed,
            "map": [],
            "buildings": [],
            "workers": [],
            "demographics": self.resource_manager.demographics,
            "historical_tax_rates": self.resource_manager.historical_tax_rates,
            "total_deaths": getattr(self.resource_manager, "total_deaths", 0),
        }

        # Save map tiles
        for x in range(self.world.grid_length_x):
            row = []
            for y in range(self.world.grid_length_y):
                row.append(self.world.world[x][y]["tile"])
            data["map"].append(row)

        # Save buildings
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                b = self.world.buildings[x][y]
                if b is not None and b.origin == (x, y):
                    building_save_data = {"name": b.name, "x": x, "y": y}
                    if getattr(b, "is_vip", False):
                        building_save_data["is_vip"] = True
                    if getattr(b, "custom_name", None):
                        building_save_data["custom_name"] = b.custom_name
                    if hasattr(b, "occupants"):
                        building_save_data["occupants"] = b.occupants
                    if hasattr(b, "is_powered"):
                        building_save_data["is_powered"] = b.is_powered
                    if isinstance(b, PowerPlant):
                        building_save_data["network_supply"] = getattr(b, "network_supply", 0)
                        building_save_data["network_demand"] = getattr(b, "network_demand", 0)
                    if isinstance(b, Tree):
                        building_save_data["is_old_tree"] = getattr(b, "is_old_tree", True)
                        if b.plant_date:
                            building_save_data["plant_date"] = b.plant_date.strftime("%Y-%m-%d")

                    if getattr(b, "on_fire", False):
                        building_save_data["on_fire"] = True
                        building_save_data["burning_time"] = pg.time.get_ticks() - b.fire_start_time

                    data["buildings"].append(building_save_data)

        # Save workers
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                w = self.world.workers[x][y]
                if w is not None:
                    data["workers"].append({"x": x, "y": y})

        # Write to JSON file
        with open(filename, "w") as f:
            json.dump(data, f)
        logger.info("Game saved successfully!")
        self.notification_text = "Game Saved!"
        self.notification_timer = pg.time.get_ticks()

    def load_game(self, filename=None):
        """Load game state from a JSON file."""
        if filename is None:
            filename = self.save_slots[0]

        if not os.path.exists(filename):
            logger.warning(f"No save file found at {filename}!")
            self.add_notification("No save file found!", (255, 100, 100))
            return

        logger.info(f"Loading game from {filename}...")
        with open(filename, "r") as f:
            data = json.load(f)

        # ============ Restore Resources & Camera ============
        self.resource_manager.funds = data.get("funds", 20_800)
        self.resource_manager.population = data.get("population", 0)
        self.resource_manager.edu_primary = data.get(
            "edu_primary", self.resource_manager.population
        )
        self.resource_manager.edu_secondary = data.get("edu_secondary", 0)
        self.resource_manager.edu_tertiary = data.get("edu_tertiary", 0)
        self.resource_manager.satisfaction = data.get("satisfaction", 100)
        self.resource_manager.years_negative_budget = data.get("years_negative_budget", 0)
        self.resource_manager.is_mayor_replaced = data.get("is_mayor_replaced", False)
        self.resource_manager.tax_per_citizen = data.get("tax_per_citizen", 10)
        self.resource_manager.total_loan_amount = data.get("total_loan_amount", 0)
        self.resource_manager.budget_history = data.get("budget_history", [])
        self.resource_manager.eviction_penalty = data.get("eviction_penalty", 0)
        self.resource_manager.demographics = {
            int(age_key): count for age_key, count in data["demographics"].items()
        }
        self.resource_manager.historical_tax_rates = data["historical_tax_rates"]
        self.resource_manager.total_deaths = data.get("total_deaths", 0)

        self.sound_on = data.get("sound_on", data.get("music_on", True))
        if self.sound_on:
            pg.mixer.music.unpause()
        else:
            pg.mixer.music.pause()

        # Restore camera position
        self.camera.scroll.x = data["camera"]["x"]
        self.camera.scroll.y = data["camera"]["y"]

        # Restore game time
        saved_date = data.get("date", "2000-01-01")
        self.current_date = datetime.datetime.strptime(saved_date, "%Y-%m-%d")
        self.current_speed = data.get("speed", 1)
        self.day_timer = 0

        # ============ Clear Current Data ============
        self.entities.clear()
        self.world.buildings = [
            [None for _ in range(self.world.grid_length_y)] for _ in range(self.world.grid_length_x)
        ]
        self.world.workers = [
            [None for _ in range(self.world.grid_length_y)] for _ in range(self.world.grid_length_x)
        ]

        # ============ Restore Map Tiles ============
        self.world.grass_tiles.fill((0, 0, 0, 0))
        center_offset_x = self.world.grass_tiles.get_width() / 2
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                tile_type = data["map"][x][y]
                self.world.world[x][y]["tile"] = tile_type
                self.world.world[x][y]["collision"] = tile_type != EntityType.BLOCK
                self.world.collision_matrix[y][x] = 1 if tile_type == EntityType.BLOCK else 0

                # Re-render grass tiles
                render_pos = self.world.world[x][y]["render_pos"]
                self.world.grass_tiles.blit(
                    self.world.tiles[EntityType.BLOCK],
                    (render_pos[0] + center_offset_x, render_pos[1]),
                )

        # ============ Restore Buildings ============
        for b_data in data["buildings"]:
            name = b_data["name"]
            x = b_data["x"]
            y = b_data["y"]
            occupants = b_data.get("occupants")

            render_pos = self.world.world[x][y]["render_pos"]
            building_class = self.construction_manager.building_types.get(name)

            if building_class:
                image = self.hud.images.get(name)
                kwargs = {}
                if name == EntityType.TREE:
                    kwargs["is_old_tree"] = b_data.get("is_old_tree", True)
                    p_date_str = b_data.get("plant_date")
                    if p_date_str:
                        kwargs["plant_date"] = datetime.datetime.strptime(p_date_str, "%Y-%m-%d")
                    else:
                        kwargs["plant_date"] = None
                ent = building_class(render_pos, image, self.resource_manager, (x, y), **kwargs)
                ent.game = self  # Set game reference

                if b_data.get("is_vip", False):
                    if hasattr(ent, "apply_vip"):
                        ent.apply_vip()

                if b_data.get("custom_name"):
                    ent.custom_name = b_data["custom_name"]

                if b_data.get("on_fire", False):
                    ent.on_fire = True
                    # Backdate the timer so it remembers how close it was to spreading
                    burning_time = b_data.get("burning_time", 0)
                    ent.fire_start_time = pg.time.get_ticks() - burning_time
                    ent.targeted_by_truck = False

                # Restore occupants if applicable
                if occupants is not None and hasattr(ent, "occupants"):
                    ent.occupants = occupants
                    if hasattr(ent, "update_image"):
                        ent.update_image()

                if "is_powered" in b_data:
                    ent.is_powered = b_data["is_powered"]
                    if hasattr(ent, "update_image"):
                        ent.update_image()
                if isinstance(ent, PowerPlant):
                    ent.network_supply = b_data.get("network_supply", 0)
                    ent.network_demand = b_data.get("network_demand", 0)

                # Add entity to world without charging cost (already paid)
                self.entities.append(ent)
                b_w = ent.grid_width
                b_h = ent.grid_height
                for i in range(x, x + b_w):
                    for j in range(y, y + b_h):
                        self.world.buildings[i][j] = ent
                        self.world.world[i][j]["collision"] = True
                        self.world.collision_matrix[j][i] = 0

        # ============ Restore Workers ============
        for w_data in data["workers"]:
            x, y = w_data["x"], w_data["y"]
            Worker(self.world.world[x][y], self.world)

        # ============ Finalize Load ============
        # Recalculate collision matrix for pathfinding
        self.world.collision_matrix = self.world.create_collision_matrix()

        self.notification_text = "Game Loaded!"
        self.notification_timer = pg.time.get_ticks()
        logger.info("Game loaded successfully!")

    def delete_save(self, filename):
        """Delete a save file."""
        if os.path.exists(filename):
            os.remove(filename)
            self.notification_text = "Save Deleted!"
            self.notification_timer = pg.time.get_ticks()

    def process_menu_overlay(self):
        """Render and handle save/load menu overlay."""
        # ============ Darken Background ============
        overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        # ============ Draw Menu Box ============
        menu_w, menu_h = 650, 400
        menu_x, menu_y = (self.width - menu_w) // 2, (self.height - menu_h) // 2
        menu_rect = pg.Rect(menu_x, menu_y, menu_w, menu_h)
        pg.draw.rect(self.screen, (40, 40, 60), menu_rect)
        pg.draw.rect(self.screen, (255, 255, 255), menu_rect, 3)

        title = f"{self.hud.active_modal} GAME"
        draw_text(self.screen, title, 50, (255, 255, 255), (menu_x + 190, menu_y + 20))

        # ============ Mouse Input Handling ============
        mouse_pos = pg.mouse.get_pos()
        mouse_state = pg.mouse.get_pressed()

        # Independent debouncing for the menu
        if not hasattr(self, "menu_mouse_pressed"):
            self.menu_mouse_pressed = False

        mouse_clicked = mouse_state[0] and not self.menu_mouse_pressed
        self.menu_mouse_pressed = mouse_state[0]

        # ============ Draw Close Button ============
        close_rect = pg.Rect(menu_x + menu_w - 45, menu_y + 15, 30, 30)
        c_color = (255, 80, 80) if close_rect.collidepoint(mouse_pos) else (200, 50, 50)
        pg.draw.rect(self.screen, c_color, close_rect, border_radius=6)
        pg.draw.rect(self.screen, (255, 255, 255), close_rect, 2, border_radius=6)
        draw_text(self.screen, "X", 30, (255, 255, 255), (close_rect.x + 8, close_rect.y + 6))

        # ============ Draw Save Slots ============
        for i, filename in enumerate(self.save_slots):
            slot_y = menu_y + 100 + (i * 80)
            slot_rect = pg.Rect(menu_x + 40, slot_y, 450, 60)
            reset_rect = pg.Rect(menu_x + 510, slot_y, 100, 60)

            # Get save file info
            info_text = "Empty Slot"
            if os.path.exists(filename):
                try:
                    with open(filename, "r") as f:
                        data = json.load(f)
                    if isinstance(data, dict):
                        # Extract saved date and population/funds
                        date = data.get("date", "Unknown")
                        funds = int(data.get("funds", 0))
                        pop = int(data.get("population", 0))
                        info_text = f"{date} | ${funds:,} | Pop: {pop}"
                    else:
                        info_text = "Corrupt Save"
                except json.JSONDecodeError:
                    info_text = "Corrupt JSON Save"
                except OSError:
                    info_text = "Unreadable Save"

            # Draw slot button
            color = (80, 80, 100) if slot_rect.collidepoint(mouse_pos) else (60, 60, 80)
            pg.draw.rect(self.screen, color, slot_rect, border_radius=6)
            pg.draw.rect(self.screen, (255, 255, 255), slot_rect, 2, border_radius=6)
            draw_text(
                self.screen,
                f"Slot {i + 1}: {info_text}",
                24,
                (255, 255, 255),
                (slot_rect.x + 15, slot_rect.y + 20),
            )

            # Draw reset button
            r_color = (200, 50, 50) if reset_rect.collidepoint(mouse_pos) else (150, 40, 40)
            pg.draw.rect(self.screen, r_color, reset_rect, border_radius=6)
            pg.draw.rect(self.screen, (255, 255, 255), reset_rect, 2, border_radius=6)
            draw_text(
                self.screen, "RESET", 24, (255, 255, 255), (reset_rect.x + 18, reset_rect.y + 20)
            )

            # ============ Handle Clicks ============
            if mouse_clicked:
                # Close button
                if close_rect.collidepoint(mouse_pos):
                    self.hud.active_modal = None
                    self.hud.mouse_pressed = True  # Prevent clicking through menu
                    return

                # Reset button
                elif reset_rect.collidepoint(mouse_pos):
                    self.delete_save(filename)

                # Slot button
                elif slot_rect.collidepoint(mouse_pos):
                    if self.hud.active_modal == "SAVE":
                        self.save_game(filename)
                    elif self.hud.active_modal == "LOAD":
                        if info_text != "Empty Slot":
                            self.load_game(filename)

                    self.hud.active_modal = None  # Close menu after action
                    self.hud.mouse_pressed = True  # Prevent clicking through menu

        # Right-click to close
        if mouse_state[2]:
            self.hud.active_modal = None
            self.hud.mouse_pressed = True

    def spawn_cars(self):
        """Spawns cars between Residential Zones and Workplaces based on population."""
        # 1. Gather eligible zones
        res_zones = [
            e
            for e in self.entities
            if isinstance(e, ResZone) and getattr(e, "occupants", 0) > 0 and e.has_road_access
        ]
        work_zones = [
            e
            for e in self.entities
            if isinstance(e, (IndZone, SerZone))
            and getattr(e, "occupants", 0) > 0
            and e.has_road_access
        ]

        if not res_zones or not work_zones:
            return

        # 2. Cap maximum cars to prevent performance drops and gridlock
        current_cars = sum(1 for e in self.entities if getattr(e, "name", "") == "Car")
        if current_cars >= 40:
            return

        # 3. Weighted choice for start zone (More occupants = higher chance to spawn)
        weights = [rz.occupants for rz in res_zones]
        start_zone = random.choices(res_zones, weights=weights, k=1)[0]
        target_zone = random.choice(work_zones)

        # 4. Spawn the car
        from .workers import Car

        Car(start_zone, target_zone, self.world)

    def _spawn_workers(self):
        """Spawn initial workers at random non-colliding locations on the map."""
        for _ in range(INITIAL_WORKER):
            spawned = False
            attempts = 0
            while not spawned and attempts < 1000:
                x = random.randint(0, self.world.grid_length_x - 1)
                y = random.randint(0, self.world.grid_length_y - 1)
                if not self.world.world[x][y]["collision"]:
                    Worker(self.world.world[x][y], self.world)
                    spawned = True
                attempts += 1
            if not spawned:
                # Failsafe: spawn at origin if map is full
                Worker(self.world.world[0][0], self.world)
