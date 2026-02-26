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
        self.hud.game = self # Give HUD a reference to game
        self.world = World(self, self.resource_manager, self.entities, self.hud, 50, 50, self.width, self.height)
        
        # Robust worker spawning: search for free tile
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
                # Failsafe if map is somehow full
                Worker(self.world.world[0][0], self.world)

        self.camera = Camera(self.width, self.height)
        self.camera.scroll.x = -(MAP_WIDTH / 2 - self.width / 2)
        self.camera.scroll.y = -(MAP_HEIGHT / 2 - self.height / 2)

        self.playing = False

        # Stars
        self.background = self.create_starry_background()
        self.star_offset = 0  # for slow swirl animation

        self.playing = False
        self.notifications = []  # List of {text, color, timer, pos_y, offset_y}

        self.menu_state = "MAIN_MENU"
        self.save_slots = ["save_slot_1.json", "save_slot_2.json", "save_slot_3.json"]

        # Sounds
        self.sounds = {
            "creation": pg.mixer.Sound("assets/sounds/creation.ogg"),
            "destruction": pg.mixer.Sound("assets/sounds/destruction.ogg"),
            "wood_chop": pg.mixer.Sound("assets/sounds/wood_chop.ogg")
        }
        
        # Music
        self.music_on = True
        try:
            pg.mixer.music.load("assets/sounds/fly_me_to_the_moon.ogg")
            pg.mixer.music.play(-1) # Loop indefinitely
        except Exception as e:
            print(f"Error loading music: {e}")

    def toggle_music(self):
        self.music_on = not self.music_on
        if self.music_on:
            pg.mixer.music.unpause()
            self.add_notification("MUSIC: ON", (100, 255, 100))
        else:
            pg.mixer.music.pause()
            self.add_notification("MUSIC: OFF", (255, 100, 100))

    def play_sound(self, sound_name):
        if sound_name in self.sounds:
            self.sounds[sound_name].play()

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
            if event.type == pg.VIDEORESIZE:
                self.width, self.height = event.w, event.h
                self.screen = pg.display.set_mode((self.width, self.height), pg.RESIZABLE)
                self.hud.width = self.width
                self.hud.height = self.height
                # Re-initialize HUD components that depend on screen size
                self.hud.__init__(self.resource_manager, self.width, self.height)
                self.camera.width = self.width
                self.camera.height = self.height
                # Update background to match new size
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
                    self.current_speed = 1
                    self.add_notification("GAME SPEED: 1x", (200, 255, 200))
                if event.key == pg.K_2:
                    self.current_speed = 2
                    self.add_notification("GAME SPEED: 2x", (255, 255, 150))
                if event.key == pg.K_3:
                    self.current_speed = 3
                    self.add_notification("GAME SPEED: 3x", (255, 150, 150))

    def add_notification(self, text, color=WHITE):
        # Position notification in the center top, but slightly staggered
        self.notifications.append({
            "text": text,
            "color": color,
            "timer": pg.time.get_ticks(),
            "offset_y": 0
        })

    def update(self):
        if self.hud.menu_action:
            if self.hud.menu_action == "SAVE":
                self.menu_state = "SAVE"
            elif self.hud.menu_action == "LOAD":
                self.menu_state = "LOAD"
            elif self.hud.menu_action == "MAIN_LOAD":
                # Find the most recently modified save file among the 3 slots
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
                self.menu_state = None # Transition to active gameplay
            
            self.hud.menu_action = None
        
        if self.menu_state == "MAIN_MENU":
            self.hud.update()
            return
        
        if self.menu_state is not None:
            return
        
        # When game over, hud.update must still run to handle the buttons
        if self.resource_manager.is_mayor_replaced:
            self.hud.update()
            return

        self.camera.update()
        self.world.update(self.camera, self.paused)
        self.hud.update()

        # Update notifications (floating up and fading)
        now = pg.time.get_ticks()
        for n in self.notifications[:]:
            if now - n["timer"] > 2500:
                self.notifications.remove(n)
            else:
                n["offset_y"] -= 1  # Float up

        if not self.paused:
            # stars
            self.star_offset += .2

            old_year = self.current_date.year
            self.day_timer += self.clock.get_time()
            if self.day_timer >= SPEEDS[self.current_speed]:
                self.current_date += datetime.timedelta(days=1)
                self.day_timer -= SPEEDS[self.current_speed]

                # DAILY BUDGET UPDATE
                self.resource_manager.apply_daily_budget(self.world)

                # Monthly/Daily population influx for small starting population
                # Check every few days for a small chance to increase population if there's capacity
                # If population < 10, it's a "starter" influx.
                # If population >= 10, it's much rarer but still possible if satisfaction is high.
                
                # Use current_date.day or a random chance per day to keep it synced with game time
                threshold_chance = 0.5 if self.resource_manager.population < 10 else 0.05
                satisfaction_bonus = self.resource_manager.satisfaction > 70
                
                if random.random() < threshold_chance and (self.resource_manager.population < 10 or satisfaction_bonus): 
                     from .buildings import ResZone
                     res_zones = []
                     for x in range(self.world.grid_length_x):
                         for y in range(self.world.grid_length_y):
                             b = self.world.buildings[x][y]
                             if isinstance(b, ResZone) and b.has_road_access and b.occupants < b.capacity:
                                 res_zones.append(b)
                     
                     if res_zones:
                         target = random.choice(res_zones)
                         target.occupants += 1
                         target.update_image()
                         # Re-sync population from actual occupants to avoid drift
                         self.resource_manager.population = sum(rz.occupants for rz in res_zones if hasattr(rz, 'occupants') and rz.name == "ResZone")
                            
                         if self.resource_manager.population <= 10:
                             self.add_notification("New citizen moved in!", (50, 255, 50))
                         else:
                             # Still notify but maybe with a different flavor for larger growth
                             self.add_notification("City is growing!", (150, 255, 150))
                         
                         # Trigger workplace recalculation when someone moves in
                         self.calculate_satisfaction_and_growth()

            if self.current_date.year > old_year:
                self.apply_annual_logic()

            for e in self.entities:
                e.update(self.current_speed)

        # Update notifications (floating up and fading)
        now = pg.time.get_ticks()
        for n in self.notifications[:]:
            if now - n["timer"] > 2500:
                self.notifications.remove(n)
            else:
                n["offset_y"] -= 1  # Float up

    def apply_annual_logic(self):
        # 1. Budget Summary Notification
        # We don't call apply_annual_budget anymore as it's daily.
        # But we can still show an annual summary.
        current_year = self.current_date.year - 1 # Logic triggers at start of new year
        year_entry = next((item for item in self.resource_manager.budget_history if item.get("year") == current_year), None)
        
        if year_entry:
            tax = int(year_entry["income"])
            maintenance = int(year_entry["expenses"])
            self.add_notification("TAXING TIME!", (255, 215, 0))
            self.add_notification(f"Annual Budget: +${tax} -${maintenance}", (100, 255, 100) if tax >= maintenance else (255, 100, 100))

        # 2. Population Dynamics & Satisfaction
        self.calculate_satisfaction_and_growth()

        # 3. Check for Game Over
        if self.resource_manager.funds < 0:
            self.resource_manager.years_negative_budget += 1
        else:
            self.resource_manager.years_negative_budget = 0

        if self.resource_manager.satisfaction < 10:
             self.resource_manager.is_mayor_replaced = True
             self.add_notification("YOU ARE FIRED!!!!", (255, 0, 0))
        
        if self.resource_manager.years_negative_budget > 5:
             self.resource_manager.is_mayor_replaced = True
             self.add_notification("GAME OVER: DEBT LIMIT EXCEEDED", (255, 0, 0))

    def calculate_satisfaction_and_growth(self):
        from .buildings import ResZone, IndZone, SerZone, Road
        from collections import deque
        # Gather all zones
        res_zones = []
        ind_zones = []
        ser_zones = []
        services = [] # Police, Stadium
        roads = []
        processed = set()
        
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                b = self.world.buildings[x][y]
                if b and b not in processed:
                    processed.add(b)
                    if isinstance(b, ResZone): res_zones.append(b)
                    elif isinstance(b, IndZone): ind_zones.append(b)
                    elif isinstance(b, SerZone): ser_zones.append(b)
                    elif isinstance(b, Road): roads.append(b)
                    elif b.name in ["Police", "Stadium"]: services.append(b)

        # Update road access for all buildings annually
        for e in self.entities:
            if hasattr(e, "has_road_access"):
                e.has_road_access = self.world.has_road_access(e.origin[0], e.origin[1], e.grid_width, e.grid_height)

        # --- ROAD NETWORK CONNECTIVITY ---
        # Map each road to its "network ID" using BFS
        road_networks = {} # (x, y) -> network_id
        next_network_id = 0
        visited_roads = set()

        for r in roads:
            rx, ry = r.origin
            if (rx, ry) not in visited_roads:
                # Start a new network BFS
                queue = deque([(rx, ry)])
                visited_roads.add((rx, ry))
                while queue:
                    cx, cy = queue.popleft()
                    road_networks[(cx, cy)] = next_network_id
                    # Check neighbors
                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < self.world.grid_length_x and 0 <= ny < self.world.grid_length_y:
                            nb = self.world.buildings[nx][ny]
                            if isinstance(nb, Road) and (nx, ny) not in visited_roads:
                                visited_roads.add((nx, ny))
                                queue.append((nx, ny))
                next_network_id += 1

        # Map zones to the set of road networks they touch
        def get_touched_networks(zone):
            adj_roads = self.world.get_adjacent_roads(zone.origin[0], zone.origin[1], zone.grid_width, zone.grid_height)
            return {road_networks[r_pos] for r_pos in adj_roads if r_pos in road_networks}

        res_zone_networks = {rz: get_touched_networks(rz) for rz in res_zones}
        ind_zone_networks = {iz: get_touched_networks(iz) for iz in ind_zones}
        ser_zone_networks = {sz: get_touched_networks(sz) for sz in ser_zones}

        # Satisfaction logic
        total_sat = 100
        
        # - Negative budget impact (Proportional to size of loan and years negative)
        if self.resource_manager.total_loan_amount > 0:
            # Penalty based on loan size (relative to a base of 1000) and years negative
            loan_penalty = (self.resource_manager.total_loan_amount / 1000) * (1 + self.resource_manager.years_negative_budget)
            total_sat -= int(loan_penalty)
            
        # - Tax impact (High taxes reduce satisfaction)
        # Assuming base tax is 10. Every $1 above 10 reduces satisfaction by 2.
        tax_impact = 0
        if self.resource_manager.tax_per_citizen > 10:
            tax_impact = (self.resource_manager.tax_per_citizen - 10) * 2
            total_sat -= tax_impact
        elif self.resource_manager.tax_per_citizen < 10:
            # Low taxes bonus
            tax_impact = (10 - self.resource_manager.tax_per_citizen) * 1
            total_sat += tax_impact
        
        # - Unbalanced industrial/service production
        total_ind_occ = sum(z.occupants for z in ind_zones)
        total_ser_occ = sum(z.occupants for z in ser_zones)
        
        imbalance_penalty = 0
        if total_ind_occ > 0 or total_ser_occ > 0:
            # If one is much larger than the other
            if total_ind_occ > 0 and total_ser_occ > 0:
                ratio = total_ind_occ / total_ser_occ
                if ratio > 2.0 or ratio < 0.5:
                    imbalance_penalty = 15
                    total_sat -= imbalance_penalty
            else:
                # If only one type has workers, it's very unbalanced
                imbalance_penalty = 20
                total_sat -= imbalance_penalty
        
        # Calculate individual zone satisfaction for ALL zones (Res, Ind, Ser)
        all_zones = res_zones + ind_zones + ser_zones
        for rz in all_zones:
            rz.local_satisfaction = total_sat
            if not rz.has_road_access:
                rz.local_satisfaction = 0 # No satisfaction if no road
                rz.bonuses = [] # Clear bonuses if no road access
                continue

            rz_networks = get_touched_networks(rz)
            if not rz_networks:
                rz.local_satisfaction = 0
                rz.bonuses = ["Disconnected road!"]
                continue

            # Add global bonuses/penalties to individual zones for HUD display
            rz.bonuses = []
            if self.resource_manager.total_loan_amount > 0:
                rz.bonuses.append(f"Debt Penalty (-{int(loan_penalty)})")
            
            if self.resource_manager.tax_per_citizen > 10:
                rz.bonuses.append(f"High Taxes (-{tax_impact})")
            elif self.resource_manager.tax_per_citizen < 10:
                rz.bonuses.append(f"Low Taxes (+{tax_impact})")
            
            if imbalance_penalty > 0:
                rz.bonuses.append(f"Imbalance Penalty (-{imbalance_penalty})")

            # Police/Stadium bonus
            for s in services:
                # Service building itself needs road access to provide benefit
                if not s.has_road_access: continue
                
                # Check if service building is reachable from the zone by road
                s_networks = get_touched_networks(s)
                if not rz_networks.intersection(s_networks):
                    continue

                dist = ((rz.origin[0]+rz.grid_width/2 - (s.origin[0]+s.grid_width/2))**2 + 
                        (rz.origin[1]+rz.grid_height/2 - (s.origin[1]+s.grid_height/2))**2)**0.5
                if s.name == "Police" and dist < POLICE_RADIUS:
                    rz.local_satisfaction += 10
                    rz.bonuses.append("Safety Bonus (+10)")
                if s.name == "Stadium" and dist < STADIUM_RADIUS:
                    rz.local_satisfaction += 15
                    rz.bonuses.append("Stadium Bonus (+15)")
            
            # Proximity to Industry (Negative for Residential)
            if isinstance(rz, ResZone):
                for iz in ind_zones:
                    dist = ((rz.origin[0]+rz.grid_width/2 - (iz.origin[0]+iz.grid_width/2))**2 + 
                            (rz.origin[1]+rz.grid_height/2 - (iz.origin[1]+iz.grid_height/2))**2)**0.5
                    if dist < INDUSTRIAL_NEGATIVE_RADIUS:
                        rz.local_satisfaction -= 10
                        rz.bonuses.append("Industrial Pollution (-10)")
            
            rz.local_satisfaction = max(0, min(100, rz.local_satisfaction))

        # Overall average satisfaction (only road-accessible zones contribute to city happiness)
        # Also require at least one road connection for it to contribute positively
        road_res = [z for z in res_zones if z.has_road_access and get_touched_networks(z)]
        if road_res:
            self.resource_manager.satisfaction = sum(z.local_satisfaction for z in road_res) / len(road_res)
        elif not res_zones:
            # No residential zones at all
            self.resource_manager.satisfaction = 100
        else:
            # Have residential zones but none have road access
            self.resource_manager.satisfaction = 30 # Low satisfaction baseline if no one can move in

        # Growth logic
        growth_potential = 0
        if self.resource_manager.satisfaction > 50:
            # Base growth is higher if population is low to kickstart the city
            base_growth = 5 if self.resource_manager.population < 20 else 2
            growth_potential = int((self.resource_manager.satisfaction - 50) / 5) + base_growth
        elif self.resource_manager.satisfaction < 30:
            growth_potential = -3
            
        if growth_potential > 0:
            self.add_notification(f"City Population Growth: +{growth_potential}", (100, 255, 100))
            for _ in range(growth_potential):
                eligible = [rz for rz in res_zones if rz.occupants < rz.capacity and rz.has_road_access]
                if eligible:
                    target = random.choice(eligible)
                    target.occupants += 1
                    # Update image will be handled at the end of calculate_satisfaction_and_growth
            # Re-sync population after all growth
            self.resource_manager.population = sum(rz.occupants for rz in res_zones)
        elif growth_potential < 0:
             self.add_notification(f"PEOPLE ARE LEAVING: {growth_potential}", (255, 100, 100))
             for _ in range(abs(growth_potential)):
                eligible = [rz for rz in res_zones if rz.occupants > 0]
                if eligible:
                    target = random.choice(eligible)
                    target.occupants -= 1
                    # Update image will be handled at the end of calculate_satisfaction_and_growth
             # Re-sync population after all decline
             self.resource_manager.population = sum(rz.occupants for rz in res_zones)

        # Workplace assignments
        # 1. Reset occupants for all zones
        for iz in ind_zones: iz.occupants = 0
        for sz in ser_zones: sz.occupants = 0
        
        # 2. Total workers available (limited by those living in ResZones)
        # Distribute workers from each ResZone to reachable Ind/Ser zones
        for rz in res_zones:
            if rz.occupants == 0 or not rz.has_road_access:
                continue
            
            rz_networks = get_touched_networks(rz)
            if not rz_networks:
                rz.local_satisfaction = 0 # No satisfaction if no road connection
                rz.bonuses = ["No road connection!"]
                continue
                
            # Find all reachable workplaces for THIS specific residential zone
            reachable_ind = [iz for iz in ind_zones if iz.has_road_access and ind_zone_networks[iz].intersection(rz_networks)]
            reachable_ser = [sz for sz in ser_zones if sz.has_road_access and ser_zone_networks[sz].intersection(rz_networks)]
            
            if not reachable_ind and not reachable_ser:
                 rz.bonuses.append("No reachable workplaces!")
                 # Some people might move out if they can't find work? 
                 # For now, just a visual indicator.
            
            # Distribute workers of this zone
            for _ in range(rz.occupants):
                eligible_ind = [z for z in reachable_ind if z.occupants < z.capacity]
                eligible_ser = [z for z in reachable_ser if z.occupants < z.capacity]
                
                target = None
                if eligible_ind and eligible_ser:
                    current_ind_occ = sum(z.occupants for z in ind_zones)
                    current_ser_occ = sum(z.occupants for z in ser_zones)
                    
                    if current_ind_occ <= current_ser_occ:
                        target = random.choice(eligible_ind)
                    else:
                        target = random.choice(eligible_ser)
                elif eligible_ind:
                    target = random.choice(eligible_ind)
                elif eligible_ser:
                    target = random.choice(eligible_ser)
                
                if target:
                    target.occupants += 1
        
        # 3. Update images for all industrial and service zones once at the end
        for iz in ind_zones: iz.update_image()
        for sz in ser_zones: sz.update_image()
        for rz in res_zones: rz.update_image()

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

        if self.notifications:
            now = pg.time.get_ticks()
            for i, n in enumerate(self.notifications):
                elapsed = now - n["timer"]
                if elapsed < 2500:
                    # Fade out alpha
                    alpha = 255
                    if elapsed > 1500:
                        alpha = int(255 * (1 - (elapsed - 1500) / 1000))
                    
                    # Modern games use vibrant colors and outlined text for readability
                    color = list(n["color"])
                    # We can't easily do alpha on draw_text without surface, but we can dim the color
                    if alpha < 255:
                        color = [int(c * (alpha/255)) for c in color]
                    
                    # Each new notification starts at 150 (lowered to avoid webcam), and they push each other down visually
                    # or they float up. The offset_y is negative.
                    draw_text(
                        self.screen,
                        n["text"],
                        40,
                        tuple(color),
                        (self.width // 2 - 200, 150 + (i * 45) + n["offset_y"])
                    )

        pg.display.flip()

    def quit_game(self):
        """Helper method to handle clean exits."""
        self.playing = False
        pg.quit()
        sys.exit()

    def restart_game(self):
        """Re-initializes the game state."""
        self.__init__(self.screen, self.clock)
        self.menu_state = None # Start playing immediately when restarting
        self.playing = True # Ensure it continues running
        self.hud.menu_action = None # Clear any lingering menu actions

    def save_game(self, filename=None):
        if filename is None:
            filename = self.save_slots[0]
        print(f"Saving game to {filename}...")
        data = {
            "funds": self.resource_manager.funds,
            "population": self.resource_manager.population,
            "satisfaction": self.resource_manager.satisfaction,
            "years_negative_budget": self.resource_manager.years_negative_budget,
            "is_mayor_replaced": self.resource_manager.is_mayor_replaced,
            "tax_per_citizen": self.resource_manager.tax_per_citizen,
            "total_loan_amount": self.resource_manager.total_loan_amount,
            "budget_history": self.resource_manager.budget_history,
            "music_on": self.music_on,

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
                row.append(self.world.world[x][y]["tile"])
            data["map"].append(row)

       # 2. Save Buildings
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                b = self.world.buildings[x][y]
                if b is not None and b.origin == (x,y):
                    building_save_data = {"name": b.name, "x": x, "y": y}
                    if hasattr(b, "occupants"):
                        building_save_data["occupants"] = b.occupants
                    data["buildings"].append(building_save_data)

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

    def load_game(self, filename=None):
        if filename is None:
            filename = self.save_slots[0]
            
        if not os.path.exists(filename):
            print(f"No save file found at {filename}!")
            self.add_notification("No save file found!", (255, 100, 100))
            return

        print(f"Loading game from {filename}...")
        with open(filename, "r") as f:
            data = json.load(f)

        # 1. Restore Resources & Camera
        self.resource_manager.funds = data.get("funds", 20_800)
        self.resource_manager.population = data.get("population", 0)
        self.resource_manager.satisfaction = data.get("satisfaction", 100)
        self.resource_manager.years_negative_budget = data.get("years_negative_budget", 0)
        self.resource_manager.is_mayor_replaced = data.get("is_mayor_replaced", False)
        self.resource_manager.tax_per_citizen = data.get("tax_per_citizen", 10)
        self.resource_manager.total_loan_amount = data.get("total_loan_amount", 0)
        self.resource_manager.budget_history = data.get("budget_history", [])
        
        # Restore music state
        self.music_on = data.get("music_on", True)
        if self.music_on:
            pg.mixer.music.unpause()
        else:
            pg.mixer.music.pause()

        self.camera.scroll.x = data["camera"]["x"]
        self.camera.scroll.y = data["camera"]["y"]

        saved_date = data.get("date", "2000-01-01")
        self.current_date = datetime.datetime.strptime(saved_date, "%Y-%m-%d")
        self.current_speed = data.get("speed", 1)
        self.day_timer = 0

        # 2. Clear current entities and map data
        self.entities.clear()
        self.world.buildings = [[None for _ in range(self.world.grid_length_y)] for _ in
                                range(self.world.grid_length_x)]
        self.world.workers = [[None for _ in range(self.world.grid_length_y)] for _ in
                              range(self.world.grid_length_x)]

        # 3. Restore Map Tiles
        self.world.grass_tiles.fill((0,0,0,0))
        center_offset_x = self.world.grass_tiles.get_width() / 2
        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                tile_type = data["map"][x][y]
                self.world.world[x][y]["tile"] = tile_type
                # If there's a rock or tree, there's a collision
                self.world.world[x][y]["collision"] = (tile_type != "")
                self.world.collision_matrix[y][x] = 1 if tile_type == "" else 0
                
                # Re-render grass tiles with base blocks
                render_pos = self.world.world[x][y]["render_pos"]
                self.world.grass_tiles.blit(
                    self.world.tiles["block"],
                    (render_pos[0] + center_offset_x, render_pos[1])
                )

        # 4. Restore Buildings
        for b_data in data["buildings"]:
            name = b_data["name"]
            x = b_data["x"]
            y = b_data["y"]
            occupants = b_data.get("occupants")

            render_pos = self.world.world[x][y]["render_pos"]
            building_class = self.world.building_types.get(name)

            if building_class:
                image = self.hud.images.get(name)
                ent = building_class(render_pos, image, self.resource_manager, (x,y))
                ent.game = self # Set game reference
                if occupants is not None and hasattr(ent, "occupants"):
                    ent.occupants = occupants
                    if hasattr(ent, "update_image"):
                        ent.update_image()

                # BUG PREVENTION: Buildings now require manual charging.
                # When loading, we just create the entity without calling apply_cost_to_resource.

                self.entities.append(ent)
                b_w = ent.grid_width
                b_h = ent.grid_height
                for i in range(x,x+b_w):
                    for j in range(y,y+b_h):
                        self.world.buildings[i][j] = ent
                        self.world.world[i][j]["collision"] = True
                        self.world.collision_matrix[j][i] = 0

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
                   # Extract saved date and population/funds for more info
                   date = data.get('date', 'Unknown')
                   funds = int(data.get('funds', 0))
                   pop = int(data.get('population', 0))
                   info_text = f"{date} | ${funds:,} | Pop: {pop}"
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