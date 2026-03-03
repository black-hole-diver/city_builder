import pygame as pg
import sys
import random

from .world import World
from .utils import draw_text, get_line
from .camera import Camera
from .hud import Hud
from .workers import Worker
from .resource_manager import ResourceManager
from .buildings import ResZone, IndZone, SerZone, Road
from .event_bus import EventBus
from .setting import (
    SPEEDS,
    INITIAL_WORKER,
    MAP_WIDTH,
    MAP_HEIGHT,
    WHITE,
    POWER_PLANT_SUPPLY,
    POLICE_RADIUS,
    STADIUM_RADIUS,
    INDUSTRIAL_NEGATIVE_RADIUS,
    BACKGROUND_COLOR,
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
        self.hud.game = self  # Give HUD a reference to game
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
        self.menu_state = "MAIN_MENU"
        self.save_slots = ["save_slot_1.json", "save_slot_2.json", "save_slot_3.json"]

        # ============ Demolition Tracker ==========
        self.demolish_target_pos = None
        self.demolish_stats = {}

        # ============ Audio System ============
        self.sounds = {
            "creation": pg.mixer.Sound("assets/sounds/creation.ogg"),
            "destruction": pg.mixer.Sound("assets/sounds/destruction.ogg"),
            "wood_chop": pg.mixer.Sound("assets/sounds/wood_chop.ogg"),
        }

        # Load and play background music
        self.sound_on = True
        try:
            pg.mixer.music.load("assets/sounds/fly_me_to_the_moon.ogg")
            pg.mixer.music.set_volume(0.1)  # Set volume to 10% (0.0 to 1.0)
            pg.mixer.music.play(-1)  # Loop indefinitely
        except Exception as e:
            print(f"Error loading music: {e}")

        EventBus.subscribe("play_sound", self.play_sound)
        EventBus.subscribe("notify", self.add_notification)
        EventBus.subscribe("recalculate_satisfaction", self.calculate_satisfaction_and_growth)
        EventBus.subscribe("toggle_music", self.toggle_music)
        EventBus.subscribe("start_rampage", self.start_rampage)

    def toggle_music(self):
        self.sound_on = not self.sound_on
        if self.sound_on:
            pg.mixer.music.unpause()
            self.add_notification("SOUND: ON", (100, 255, 100))
        else:
            pg.mixer.music.pause()
            self.add_notification("SOUND: OFF", (255, 100, 100))

    def play_sound(self, sound_name):
        if self.sound_on and sound_name in self.sounds:
            self.sounds[sound_name].play()

    def create_starry_background(self):
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
                if event.key == pg.K_ESCAPE:
                    if self.hud.show_help:
                        self.hud.show_help = False
                    elif self.hud.show_budget:
                        self.hud.show_budget = False
                    elif self.menu_state is not None:
                        self.menu_state = None
                    else:
                        self.quit_game()
                if event.key == pg.K_SPACE:
                    self.paused = not self.paused
                if event.key == pg.K_F5:
                    self.menu_state = "SAVE"
                if event.key == pg.K_F9:
                    self.menu_state = "LOAD"

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

    def add_notification(self, text, color=WHITE):
        """Add a notification message that floats up and fades out."""
        self.notifications.append(
            {"text": text, "color": color, "timer": pg.time.get_ticks(), "offset_y": 0}
        )

    def update(self):
        """Update game state, handle menu actions, and process game logic."""
        # ============ Handle Menu Actions ============
        if self.hud.menu_action:
            if self.hud.menu_action == "SAVE":
                self.menu_state = "SAVE"
            elif self.hud.menu_action == "LOAD":
                self.menu_state = "LOAD"
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
                    self.menu_state = None
                else:
                    self.add_notification("No save files found!", (255, 100, 100))
            elif self.hud.menu_action == "RESTART":
                self.restart_game()
            elif self.hud.menu_action == "PLAY":
                self.menu_state = None  # Transition to active gameplay

            self.hud.menu_action = None

        # ============ Menu State Handling ============
        if self.menu_state == "MAIN_MENU":
            self.hud.update()
            return

        if self.menu_state is not None:
            return

        # Game over state: HUD must still update to handle buttons
        if self.resource_manager.is_mayor_replaced:
            self.hud.update()
            return

        # ============ Core Game Updates ============
        self.camera.update()
        self.world.update(self.camera, self.paused)
        self.hud.update()

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
                threshold_chance = 0.5 if self.resource_manager.population < 10 else 0.05
                satisfaction_bonus = self.resource_manager.satisfaction > 70

                if random.random() < threshold_chance and (
                    self.resource_manager.population < 10 or satisfaction_bonus
                ):
                    # Find all eligible residential zones with capacity
                    res_zones = [
                        b
                        for b in self.entities
                        if isinstance(b, ResZone) and b.has_road_access and b.occupants < b.capacity
                    ]

                    if res_zones:
                        target = random.choice(res_zones)
                        target.occupants += 1
                        target.update_image()

                        # Sync population count to prevent drift
                        all_res_zones = [b for b in self.entities if isinstance(b, ResZone)]
                        self.resource_manager.population = sum(rz.occupants for rz in all_res_zones)

                        # Display appropriate notification
                        if self.resource_manager.population <= 10:
                            self.add_notification("New citizen moved in!", (50, 255, 50))
                        else:
                            self.add_notification("City is growing!", (150, 255, 150))

                        # Recalculate satisfaction and workplace assignments
                        self.calculate_satisfaction_and_growth()

            # --- Annual Logic Trigger ---
            if self.current_date.year > old_year:
                self.apply_annual_logic()

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

    def start_rampage(self):
        """Triggers the Dinosaur Rampage event."""
        self.rampage_active = True
        self.rampage_timer = pg.time.get_ticks()
        self.add_notification("DINOSAUR IS COMINGGGG!!!!!!!", (255, 50, 50))

        # 1. Spawn Dinosaur
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

        # 2. Swap Soundtrack
        try:
            pg.mixer.music.load("assets/sounds/dino_song_epic.ogg")
            pg.mixer.music.set_volume(0.4)
            if self.sound_on:
                pg.mixer.music.play()  # Play once
        except Exception as e:
            print(f"Error loading dino music: {e}")

    def end_rampage(self):
        """Concludes the Dinosaur Rampage event and calculates casualties."""
        self.rampage_active = False
        self.add_notification("THE DINOSAUR LEFT...", (200, 200, 200))

        # 1. Remove Dinosaur Entity
        if self.dinosaur_entity in self.entities:
            self.entities.remove(self.dinosaur_entity)
        self.dinosaur_entity = None

        # 2. Calculate Casualties (5% to 20% of total population)
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

            # Resync total population
            all_res_zones = [e for e in self.entities if isinstance(e, ResZone)]
            self.resource_manager.population = sum(rz.occupants for rz in all_res_zones)

            # Instantly recalculate satisfaction to reflect empty houses/lost taxes
            self.calculate_satisfaction_and_growth()

        # 3. Restore Main Soundtrack
        pg.mixer.music.load("assets/sounds/fly_me_to_the_moon.ogg")
        pg.mixer.music.set_volume(0.1)
        if self.sound_on:
            pg.mixer.music.play(-1)

    def apply_annual_logic(self):
        """Handle annual events: budget summary, satisfaction, and game over conditions."""
        # ============ Annual Budget Summary ============
        # Budget is applied daily, but show annual summary
        current_year = self.current_date.year - 1  # Logic triggers at start of new year
        year_entry = next(
            (
                item
                for item in self.resource_manager.budget_history
                if item.get("year") == current_year
            ),
            None,
        )

        if year_entry:
            tax = int(year_entry["income"])
            maintenance = int(year_entry["expenses"])
            self.add_notification("TAXING TIME!", (255, 215, 0))
            self.add_notification(
                f"Annual Budget: +${tax} -${maintenance}",
                (100, 255, 100) if tax >= maintenance else (255, 100, 100),
            )

        # Attrition (Death/Retirement)

        attrition_rate = 0.10
        retired_sec = int(self.resource_manager.edu_secondary * attrition_rate)
        retired_tert = int(self.resource_manager.edu_tertiary * attrition_rate)
        self.resource_manager.edu_secondary -= retired_sec
        self.resource_manager.edu_primary += retired_sec
        self.resource_manager.edu_tertiary -= retired_tert
        self.resource_manager.edu_secondary += retired_tert

        # Graduation
        sec_cap = int(self.resource_manager.population * 0.50)
        tert_cap = int(self.resource_manager.population * 0.25)

        schools = [
            e
            for e in self.entities
            if e.name == "School" and e.has_road_access and getattr(e, "is_powered", False)
        ]
        unis = [
            e
            for e in self.entities
            if e.name == "University" and e.has_road_access and getattr(e, "is_powered", False)
        ]

        # Schools graduate Primary -> Secondary
        for s in schools:
            # Each school can handle a specific number of students per year
            potential = min(20, getattr(s, "occupants", 0))
            graduates = min(
                potential,
                self.resource_manager.edu_primary,
                max(0, sec_cap - self.resource_manager.edu_secondary),
            )
            self.resource_manager.edu_primary -= graduates
            self.resource_manager.edu_secondary += graduates

        # Universities graduate Secondary -> Tertiary
        for u in unis:
            potential = min(10, getattr(u, "occupants", 0))
            graduates = min(
                potential,
                self.resource_manager.edu_secondary,
                max(0, tert_cap - self.resource_manager.edu_tertiary),
            )
            self.resource_manager.edu_secondary -= graduates
            self.resource_manager.edu_tertiary += graduates

        if len(schools) > 0 or len(unis) > 0:
            self.add_notification("ACADEMIC YEAR COMPLETE", (100, 200, 255))

        # ============ Population Dynamics & Satisfaction ============
        self.calculate_satisfaction_and_growth()

        # ============ Game Over Conditions ============
        # Track consecutive years with negative budget
        if self.resource_manager.funds < 0:
            self.resource_manager.years_negative_budget += 1
        else:
            self.resource_manager.years_negative_budget = 0

        # Game over: satisfaction too low
        if self.resource_manager.satisfaction < 10:
            self.resource_manager.is_mayor_replaced = True
            self.add_notification("YOU ARE FIRED!!!!", (255, 0, 0))

        # Game over: debt limit exceeded
        if self.resource_manager.years_negative_budget > 5:
            self.resource_manager.is_mayor_replaced = True
            self.add_notification("GAME OVER: DEBT LIMIT EXCEEDED", (255, 0, 0))

    @staticmethod
    def get_power_networks(power_capable):
        """BFS algorithm to group adjacent buildings into contiguous power grids."""
        from collections import deque

        visited_power = set()
        power_networks = []

        for b in power_capable:
            if b not in visited_power:
                network = []
                queue = deque([b])
                visited_power.add(b)

                while queue:
                    curr = queue.popleft()
                    network.append(curr)

                    for other in power_capable:
                        if other not in visited_power:
                            x_overlap = (
                                curr.origin[0] < other.origin[0] + other.grid_width
                                and curr.origin[0] + curr.grid_width > other.origin[0]
                            )
                            y_overlap = (
                                curr.origin[1] < other.origin[1] + other.grid_height
                                and curr.origin[1] + curr.grid_height > other.origin[1]
                            )

                            x_adj = (
                                curr.origin[0] == other.origin[0] + other.grid_width
                                or curr.origin[0] + curr.grid_width == other.origin[0]
                            ) and y_overlap
                            y_adj = (
                                curr.origin[1] == other.origin[1] + other.grid_height
                                or curr.origin[1] + curr.grid_height == other.origin[1]
                            ) and x_overlap

                            if x_adj or y_adj:
                                visited_power.add(other)
                                queue.append(other)

                power_networks.append(network)

        return power_networks

    def calculate_satisfaction_and_growth(self):
        """Calculate satisfaction levels, population growth, and workplace assignments."""
        res_zones, ind_zones, ser_zones, services, roads = self._zone_distribution()
        self._update_road_access()
        road_networks = self._get_road_networks()
        self._calculate_power_connectivity()

        # --- Workforce and Job Availability Calculation ---
        total_ind_jobs = sum(z.capacity for z in ind_zones if z.has_road_access)
        total_ser_jobs = sum(z.capacity for z in ser_zones if z.has_road_access)
        workforce = sum(rz.occupants for rz in res_zones)
        total_jobs_available = total_ind_jobs + total_ser_jobs
        all_zones = res_zones + ind_zones + ser_zones

        # --- Negative Satisfaction Base ---
        lingering_eviction_penalty = self._calculate_lingering_eviction_penalty()
        loan_penalty = self._calculate_loan_penalty()
        tax_impact = self._calculate_tax_impact()
        imbalance_penalty = self._calculate_industrial_service_imbalance_penalty(
            total_ind_jobs, total_ser_jobs)

        total_sat = 100 - (imbalance_penalty + loan_penalty
                + lingering_eviction_penalty) + tax_impact

        # -- Calculate Individual Zone Satisfaction and Bonuses ---
        self._calculate_individual_zone_satisfaction(all_zones, total_sat, road_networks,
                                                total_jobs_available, workforce, loan_penalty,
                                                tax_impact, imbalance_penalty, services, ind_zones)
        self._calculate_overall_city_satisfaction(res_zones)
        self._calculate_population_growth(res_zones, ind_zones, ser_zones)

        # -- Education and Workplace Assignments ---
        self._workplace_assignment(ind_zones, ser_zones, res_zones)
        self._update_zone_images(ind_zones, ser_zones, res_zones)
        self._education_assignment()

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)

        for star in self.stars:
            x, y, radius, brightness = star

            glow_color = (brightness, brightness, 180)
            pg.draw.circle(self.screen, glow_color, (x, y), radius)

        if self.menu_state == "MAIN_MENU":
            self.hud.draw_main_menu(self.screen)
            pg.display.flip()
            return

        self.world.draw(self.screen, self.camera)
        self.hud.draw(self.screen, self.current_date, self.current_speed)

        if self.menu_state in ["SAVE", "LOAD"]:
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
            for i, n in enumerate(self.notifications):
                elapsed = now - n["timer"]
                if elapsed < 2500:
                    # Calculate fade-out alpha
                    alpha = 255
                    if elapsed > 1500:
                        alpha = int(255 * (1 - (elapsed - 1500) / 1000))

                    # Apply alpha by dimming color
                    color = list(n["color"])
                    if alpha < 255:
                        color = [int(c * (alpha / 255)) for c in color]

                    # Draw notification with float-up animation
                    draw_text(
                        self.screen,
                        n["text"],
                        40,
                        tuple(color),
                        (self.width // 2 - 200, 150 + (i * 45) + n["offset_y"]),
                    )

        pg.display.flip()

    def quit_game(self):
        """Handle clean game exit."""
        self.playing = False
        pg.quit()
        sys.exit()

    def restart_game(self):
        """Reinitialize the game state for a fresh start."""
        self.__init__(self.screen, self.clock)
        self.menu_state = None  # Start playing immediately
        self.playing = True
        self.hud.menu_action = None  # Clear lingering menu actions

    def save_game(self, filename=None):
        """Save current game state to a JSON file."""
        if filename is None:
            filename = self.save_slots[0]
        print(f"Saving game to {filename}...")
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
                    if hasattr(b, "occupants"):
                        building_save_data["occupants"] = b.occupants
                    if hasattr(b, "is_powered"):
                        building_save_data["is_powered"] = b.is_powered
                    if b.name == "PowerPlant":
                        building_save_data["network_supply"] = getattr(b, "network_supply", 0)
                        building_save_data["network_demand"] = getattr(b, "network_demand", 0)
                    if b.name == "Tree":
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
        print("Game saved successfully!")
        self.notification_text = "Game Saved!"
        self.notification_timer = pg.time.get_ticks()

    def load_game(self, filename=None):
        """Load game state from a JSON file."""
        if filename is None:
            filename = self.save_slots[0]

        if not os.path.exists(filename):
            print(f"No save file found at {filename}!")
            self.add_notification("No save file found!", (255, 100, 100))
            return

        print(f"Loading game from {filename}...")
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

        # Restore music state
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
                self.world.world[x][y]["collision"] = tile_type != ""
                self.world.collision_matrix[y][x] = 1 if tile_type == "" else 0

                # Re-render grass tiles
                render_pos = self.world.world[x][y]["render_pos"]
                self.world.grass_tiles.blit(
                    self.world.tiles["block"], (render_pos[0] + center_offset_x, render_pos[1])
                )

        # ============ Restore Buildings ============
        for b_data in data["buildings"]:
            name = b_data["name"]
            x = b_data["x"]
            y = b_data["y"]
            occupants = b_data.get("occupants")

            render_pos = self.world.world[x][y]["render_pos"]
            building_class = self.world.building_types.get(name)

            if building_class:
                image = self.hud.images.get(name)
                kwargs = {}
                if name == "Tree":
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
                if name == "PowerPlant":
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
        print("Game loaded successfully!")

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

        title = f"{self.menu_state} GAME"
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
                    self.menu_state = None
                    self.hud.mouse_pressed = True  # Prevent clicking through menu
                    return

                # Reset button
                elif reset_rect.collidepoint(mouse_pos):
                    self.delete_save(filename)

                # Slot button
                elif slot_rect.collidepoint(mouse_pos):
                    if self.menu_state == "SAVE":
                        self.save_game(filename)
                    elif self.menu_state == "LOAD":
                        if info_text != "Empty Slot":
                            self.load_game(filename)

                    self.menu_state = None  # Close menu after action
                    self.hud.mouse_pressed = True  # Prevent clicking through menu

        # Right-click to close
        if mouse_state[2]:
            self.menu_state = None
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

    def _zone_distribution(self):
        """Distributing the zone in to lits"""
        res_zones = []
        ind_zones = []
        ser_zones = []
        services = []
        roads = []
        for entity in self.entities:
            if isinstance(entity, ResZone):
                res_zones.append(entity)
            elif isinstance(entity, IndZone):
                ind_zones.append(entity)
            elif isinstance(entity, SerZone):
                ser_zones.append(entity)
            elif isinstance(entity, Road):
                roads.append(entity)
            elif hasattr(entity, "name") and entity.name in ["Police", "Stadium"]:
                services.append(entity)
        return res_zones, ind_zones, ser_zones, services, roads

    def _update_road_access(self):
        """Update road access for all entities."""
        for e in self.entities:
            if hasattr(e, "has_road_access"):
                e.has_road_access = self.world.has_road_access(
                    e.origin[0], e.origin[1], e.grid_width, e.grid_height
                )

    def _get_road_networks(self):
        """Map each road to its network ID using BFS."""
        from collections import deque

        road_networks = {}  # (x, y) -> network_id
        next_network_id = 0
        visited_roads = set()

        for r in [e for e in self.entities if isinstance(e, Road)]:
            rx, ry = r.origin
            if (rx, ry) not in visited_roads:
                queue = deque([(rx, ry)])
                visited_roads.add((rx, ry))
                while queue:
                    cx, cy = queue.popleft()
                    road_networks[(cx, cy)] = next_network_id

                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = cx + dx, cy + dy
                        if (
                            0 <= nx < self.world.grid_length_x
                            and 0 <= ny < self.world.grid_length_y
                        ):
                            nb = self.world.buildings[nx][ny]
                            if isinstance(nb, Road) and (nx, ny) not in visited_roads:
                                visited_roads.add((nx, ny))
                                queue.append((nx, ny))
                next_network_id += 1

        return road_networks

    def _calculate_power_connectivity(self):
        """1. Identify all buildings that can conduct or produce electricity
        2. Use the standalone BFS function to find all contiguous grids
        3. Calculate Supply vs Demand per grid and update power states
        4. Distribute electricity until supply runs out, prioritizing essential services"""
        power_cable = [
            e
            for e in self.entities
            if e.name in [
                "PowerPlant",
                "PowerLine",
                "ResZone",
                "IndZone",
                "SerZone",
                "Police",
                "Stadium",
                "FireStation",
                "School",
                "University",
            ]
        ]
        for e in power_cable:
            e.is_powered = False
        power_networks = Game.get_power_networks(power_cable)
        for network in power_networks:
            power_plants = [b for b in network if b.name == "PowerPlant"]
            total_supply = len(power_plants) * POWER_PLANT_SUPPLY
            demand_list = []
            for b in network:
                if b.name in ["PowerPlant", "PowerLine"]:
                    b.is_powered = total_supply > 0
                    continue
                demand = 0
                if b.name in ["ResZone", "IndZone", "SerZone"]:
                    demand = 5 + getattr(b, "occupants", 0) * 2
                else:
                    demand = 50
                    if b.name == "Stadium":
                        demand = 200
                    elif b.name == "University":
                        demand = 100
                if demand > 0:
                    demand_list.append((b, demand))
            demand_list.sort(
                key=lambda x: 0 if x[0].name in ["ResZone", "IndZone", "SerZone"] else 1,
                reverse=True,
            )
            current_supply = total_supply
            for b, dem in demand_list:
                if current_supply >= dem:
                    current_supply -= dem
                    b.is_powered = True
                else:
                    b.is_powered = False

    def _get_touched_networks(self, zone, road_networks):
            """Get all road networks adjacent to this zone."""
            adj_roads = self.world.get_adjacent_roads(
                zone.origin[0], zone.origin[1], zone.grid_width, zone.grid_height
            )
            return {road_networks[r_pos] for r_pos in adj_roads if r_pos in road_networks}

    def _calculate_lingering_eviction_penalty(self):
        """Calculate a lingering satisfaction penalty for recent evictions.
        The penalty decays over time, as the lasting impact of evictions on citizen morale.
        Decay rate is 5 points per day, the penalty reduced by 5 each day until it reaches 0."""
        lingering_eviction_penalty = 0
        if self.resource_manager.eviction_penalty > 0:
            lingering_eviction_penalty += int(self.resource_manager.eviction_penalty)
            self.resource_manager.eviction_penalty = max(
                0, self.resource_manager.eviction_penalty - 5
            )
        return lingering_eviction_penalty

    def _calculate_loan_penalty(self):
        """Calculate a satisfaction penalty based on the city's current debt and financial health.
        The penalty is proportional to the total loan amount and increases with years."""
        loan_penalty = 0
        if self.resource_manager.total_loan_amount > 0:
            loan_penalty = (self.resource_manager.total_loan_amount / 1000) * (
                1 + self.resource_manager.years_negative_budget
            )
        return loan_penalty

    def _calculate_tax_impact(self):
        """Calculate satisfaction impact based on current tax rate.
        Higher taxes reduce satisfaction; lower taxes increase it.
        Base tax is 10. Every $1 above/below 10 affects satisfaction by a certain amount."""
        tax_impact = 0
        if self.resource_manager.tax_per_citizen > 10:
            tax_impact = -((self.resource_manager.tax_per_citizen - 10) * 2)
        elif self.resource_manager.tax_per_citizen < 10:
            tax_impact = (10 - self.resource_manager.tax_per_citizen) * 1
        return tax_impact

    def _calculate_industrial_service_imbalance_penalty(self, total_ind_jobs, total_ser_jobs):
        """Apply a penalty if there is a big imbalance between industrial and service jobs.
        A healthy city typically has a mix of both."""
        imbalance_penalty = 0
        if total_ind_jobs > 0 and total_ser_jobs > 0:
            ratio = total_ind_jobs / total_ser_jobs
            if ratio > 2.0 or ratio < 0.5:
                imbalance_penalty = 15
        elif total_ind_jobs > 0 or total_ser_jobs > 0:
            imbalance_penalty = 20
        return imbalance_penalty

    def _calculate_individual_zone_service_bonuses(self, rz, services, road_networks):
        """Calculate bonuses for a residential zone based on proximity to services."""
        for s in services:
            if not s.has_road_access or not getattr(s, "is_powered", False):
                continue

            s_networks = self._get_touched_networks(s, road_networks)
            rz_networks = self._get_touched_networks(rz, road_networks)
            if not rz_networks.intersection(s_networks):
                continue

            dist = (
                (rz.origin[0] + rz.grid_width / 2 - (s.origin[0] + s.grid_width / 2)) ** 2
                + (rz.origin[1] + rz.grid_height / 2 - (s.origin[1] + s.grid_height / 2)) ** 2
            ) ** 0.5

            if s.name == "Police" and dist < POLICE_RADIUS:
                rz.local_satisfaction += 10
                rz.bonuses.append("Safety Bonus (+10)")
            if s.name == "Stadium" and dist < STADIUM_RADIUS:
                rz.local_satisfaction += 15
                rz.bonuses.append("Stadium Bonus (+15)")

    def _calculate_individual_zone_satisfaction(self, all_zones, total_sat, road_networks,
                                                total_jobs_available, workforce, loan_penalty,
                                                tax_impact, imbalance_penalty, services, ind_zones):
        """Calculate satisfaction for a single residential zone based on various factors.
        No satisfaction if no road access or disconnected from road network.
        Penalties for lack of electricity.
        Penalties for severe job shortages."""
        for rz in all_zones:
            rz.local_satisfaction = total_sat

            # No satisfaction without road access
            if not rz.has_road_access:
                rz.local_satisfaction = 0
                rz.bonuses = ["No Road Access"]
                continue

            # No satisfaction if disconnected from road network
            rz_networks = self._get_touched_networks(rz, road_networks)
            if not rz_networks:
                rz.local_satisfaction = 0
                rz.bonuses = ["Disconnected Road!"]
                continue

            rz.bonuses = []

            # Severe penalty if not powered by electricity
            if not getattr(rz, "is_powered", False):
                rz.local_satisfaction -= 25
                rz.bonuses.append("No Electricity (-25)")

            # Severe job shortage penalty if less than 50% of workforce has access to jobs
            if isinstance(rz, ResZone):
                if workforce > 0 and total_jobs_available < (0.5 * workforce):
                    rz.local_satisfaction -= 15
                    rz.bonuses.append("Severe Job Shortage (-15)")

            # Apply financial penalties/bonuses
            if loan_penalty > 0:
                rz.bonuses.append(f"Debt Penalty (-{int(loan_penalty)})")

            if tax_impact < 0:
                rz.bonuses.append(f"High Taxes (-{abs(tax_impact)})")
            elif tax_impact > 0:
                rz.bonuses.append(f"Low Taxes (+{tax_impact})")

            # Apply industrial/service imbalance penalty
            if imbalance_penalty > 0:
                rz.bonuses.append(f"Imbalance Penalty (-{imbalance_penalty})")

            # Calculate bonuses from proximity to services (Stadium, Police)
            self._calculate_individual_zone_service_bonuses(rz, services, road_networks)
            if isinstance(rz, ResZone):
                self._calculate_industrial_pollution_penalty(rz, ind_zones)
                self._calculate_tree_bonus(rz)

            # Clamp satisfaction between 0 and 100
            rz.local_satisfaction = max(0, min(100, rz.local_satisfaction))

    def _calculate_tree_bonus(self, rz):
        """Calculate a satisfaction bonus for residential zones from nearby trees in line of sight.
        Trees provide bonus if they are within 3 squares
        and have a clear line of sight to ResZone."""
        rz.tree_bonus = 0
        all_trees = [e for e in self.entities if e.name == "Tree"]
        for tree in all_trees:
            # Get closest point on the ResZone to the tree
            cx = max(rz.origin[0], min(tree.origin[0], rz.origin[0] + rz.grid_width - 1))
            cy = max(rz.origin[1], min(tree.origin[1], rz.origin[1] + rz.grid_height - 1))

            # Check distance <= 3 squares (Chebyshev distance)
            if max(abs(cx - tree.origin[0]), abs(cy - tree.origin[1])) <= 3:
                # Check Line of Sight
                line = get_line(cx, cy, tree.origin[0], tree.origin[1])
                los = True
                for px, py in line:
                    if (px, py) == (cx, cy) or (px, py) == tree.origin:
                        continue
                    if self.world.buildings[px][py] is not None:
                        los = False
                        break

                if los:
                    # Base bonus * growth multiplier
                    bonus = 5 * tree.get_bonus_multiplier(self.current_date)
                    rz.tree_bonus += bonus

        if rz.tree_bonus > 0:
            rz.local_satisfaction += int(rz.tree_bonus)
            rz.bonuses.append(f"Nature Bonus (+{int(rz.tree_bonus)})")

    def _calculate_industrial_pollution_penalty(self, rz, ind_zones):
        """Calculate pollution penalty for a residential zone from proximity to industrial zones.
        Trees can mitigate pollution if they are between the residential and industrial zones."""
        for iz in ind_zones:
            dist = (
                (rz.origin[0] + rz.grid_width / 2 - (iz.origin[0] + iz.grid_width / 2)) ** 2
                + (rz.origin[1] + rz.grid_height / 2 - (iz.origin[1] + iz.grid_height / 2)) ** 2
            ) ** 0.5
            if dist < INDUSTRIAL_NEGATIVE_RADIUS:
                line = get_line(
                    rz.origin[0] + rz.grid_width / 2,
                    rz.origin[1] + rz.grid_height / 2,
                    iz.origin[0] + iz.grid_width / 2,
                    iz.origin[1] + iz.grid_height / 2,
                )
                forest_blocked = False
                for px, py in line:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            nx, ny = px + dx, py + dy
                            if (
                                0 <= nx < self.world.grid_length_x
                                and 0 <= ny < self.world.grid_length_y
                            ):
                                if (
                                    getattr(self.world.buildings[nx][ny], "name", "")
                                    == "Tree"
                                ):
                                    forest_blocked = True
                                    break
                        if forest_blocked:
                            break
                    if forest_blocked:
                        break

                if forest_blocked:
                    rz.local_satisfaction -= 5
                    rz.bonuses.append("Pollution (Forest Blocked) (-5)")
                else:
                    rz.local_satisfaction -= 10
                    rz.bonuses.append("Industrial Pollution (-10)")

    def _calculate_overall_city_satisfaction(self, res_zones):
        """Calculate overall city satisfaction as the average of all residential zones."""
        if res_zones:
            self.resource_manager.satisfaction = sum(z.local_satisfaction for z in res_zones) / len(
                res_zones
            )
        else:
            self.resource_manager.satisfaction = 100  # No zones = perfect satisfaction

    def _calculate_population_growth(self, res_zones, ind_zones, ser_zones):
        """Calculate population growth/decline based on overall satisfaction and other factors."""
        growth_potential = 0
        if self.resource_manager.satisfaction > 50:
            # Starter city boost: higher base growth if population < 20
            base_growth = 5 if self.resource_manager.population < 20 else 2
            growth_potential = int((self.resource_manager.satisfaction - 50) / 5) + base_growth
        elif self.resource_manager.satisfaction < 30:
            growth_potential = -3

        if growth_potential > 0:
            self.add_notification(f"City Population Growth: +{growth_potential}", (100, 255, 100))
            for _ in range(growth_potential):
                eligible = [
                    rz
                    for rz in res_zones
                    if rz.occupants < rz.capacity
                    and rz.has_road_access
                    and getattr(rz, "is_powered", False)
                ]
                if eligible:
                    weights = [1 + getattr(rz, "tree_bonus", 0) for rz in eligible]
                    target = random.choices(eligible, weights=weights, k=1)[0]
                    target.occupants += 1
                    self.resource_manager.edu_primary += 1
            # Sync population after growth
            self.resource_manager.population = sum(rz.occupants for rz in res_zones)

        # --- Apply Population Decline ---
        elif growth_potential < 0:
            self.add_notification(f"PEOPLE ARE LEAVING: {growth_potential}", (255, 100, 100))
            for _ in range(abs(growth_potential)):
                eligible = [rz for rz in res_zones if rz.occupants > 0]
                if eligible:
                    target = random.choice(eligible)
                    target.occupants -= 1
            # Sync population after decline
            self.resource_manager.population = sum(rz.occupants for rz in res_zones)

    def _workplace_assignment(self, ind_zones, ser_zones, res_zones):
        """Assign workers to industrial and service zones based on road access and fill ratio.
        1. Reset all industrial and service zone occupants to 0 before assignment.
        2. Calculate a global "Fill Ratio" based on total workforce vs total job capacity.
        3. Proportionally assign workers to each zone based on its capacity and the fill ratio.
        4. Handle any rounding remainders by distributing leftover workers 1-by-1 to random zones
        with available capacity."""

        for iz in ind_zones:
            iz.occupants = 0
        for sz in ser_zones:
            sz.occupants = 0

        workforce = sum(rz.occupants for rz in res_zones)
        ind_ser_zones = [z for z in (ind_zones + ser_zones) if z.has_road_access]

        if ind_ser_zones and workforce > 0:
            total_capacity = sum(z.capacity for z in ind_ser_zones)

            assignable_workers = min(workforce, total_capacity)
            fill_ratio = assignable_workers / total_capacity

            for zone in ind_ser_zones:
                zone.occupants = int(zone.capacity * fill_ratio)

            current_assigned = sum(z.occupants for z in ind_ser_zones)
            remainder = assignable_workers - current_assigned

            if remainder > 0:
                random.shuffle(ind_ser_zones) # Shuffle for random distribution of leftover workers
                for zone in ind_ser_zones:
                    if remainder <= 0:
                        break
                    if zone.occupants < zone.capacity:
                        zone.occupants += 1
                        remainder -= 1

    def _update_zone_images(self, ind_zones, ser_zones, res_zones):
        """Update the image of each zone based on its current satisfaction and occupancy."""
        for iz in ind_zones:
            iz.update_image()
        for sz in ser_zones:
            sz.update_image()
        for rz in res_zones:
            rz.update_image()
        for pl in self.entities:
            if getattr(pl, "name", "") == "PowerLine" and hasattr(pl, "update_image"):
                pl.update_image()

    def _allocate_students(self, entities, demand):
        """Assign students to schools based on available capacity and demand.
        1. Calculate total available capacity across all schools.
        2. Determine how many students can be assigned based on the fill ratio of demand vs cap.
        3. Proportionally assign students to each school based on its capacity and the fill ratio.
        4. Handle any rounding remainders by distributing leftover students
        one-by-one to random schools with available capacity."""
        total_capacity = sum(e.capacity for e in entities)
        if total_capacity == 0 or demand <= 0:
            for e in entities:
                e.occupants = 0
            return
        assignable = min(demand, total_capacity)
        fill_ratio = assignable / total_capacity

        for e in entities:
            e.occupants = int(e.capacity * fill_ratio)

        # Distribute rounding remainders
        remainder = assignable - sum(e.occupants for e in entities)
        if remainder > 0:
            random.shuffle(entities)
            for e in entities:
                if remainder <= 0:
                    break
                if e.occupants < e.capacity:
                    e.occupants += 1
                    remainder -= 1

    def _education_assignment(self):
        """Allocate citizens to educational institutions based on capacity and road access.
        1. Reset occupants for all Schools and Universities before assignment.
        2. Calculate total available capacity for Schools and Universities.
        3. Proportionally allocate students based on the fill ratio of demand vs capacity.
        4. Handle any rounding remainders by distributing leftover students
        one-by-one to random schools/universities with available capacity."""
        schools = [
            e
            for e in self.entities
            if e.name == "School" and e.has_road_access and getattr(e, "is_powered", False)
        ]
        unis = [
            e
            for e in self.entities
            if e.name == "University" and e.has_road_access and getattr(e, "is_powered", False)
        ]
        for s in schools:
            s.occupants = 0
        for u in unis:
            u.occupants = 0

        # Allocate students to schools and universities based on demand and capacity
        if schools and self.resource_manager.edu_primary > 0:
            self._allocate_students(schools, self.resource_manager.edu_primary)
        if unis and self.resource_manager.edu_secondary > 0:
            self._allocate_students(unis, self.resource_manager.edu_secondary)

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
