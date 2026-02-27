import pygame as pg

from .setting import *
from .utils import draw_text

class Hud:
    def __init__(self, resource_manager, width, height):
        self.music_btn_rect_main = None
        self.resource_manager = resource_manager
        self.width = width
        self.height = height
        self.hud_colour = HUD_COLOR

        # Resource HUD
        self.resource_surface = pg.Surface((width, height * 0.02), pg.SRCALPHA)
        self.resource_rect = self.resource_surface.get_rect(topleft=(0, 0))
        self.resource_surface.fill(self.hud_colour)

        # Building HUD
        self.build_surface = pg.Surface((width * 0.15, height * 0.25), pg.SRCALPHA)
        self.build_rect = self.build_surface.get_rect(topleft=(self.width * 0.84, self.height * 0.74))
        self.build_surface.fill(self.hud_colour)

        # Select HUD
        self.select_surface = pg.Surface((width * 0.3, height * 0.26), pg.SRCALPHA)
        self.select_rect = self.select_surface.get_rect(topleft=(self.width * 0.34, self.height * 0.73))
        self.select_surface.fill(self.hud_colour)

        self.images = self.load_images()
        self.tiles = self.create_build_hud()

        self.selected_tile = None

        # Internal variables for caching the examined tile's scaled image
        self._examined_tile = None
        self.examined_tile_scaled_img = None

        self.hovered_tile = None
        self.mouse_pressed = False

        self.display_names = {
            "ResZone": "Residential Zone",
            "IndZone": "Industrial Zone",
            "SerZone": "Service Zone",
            "FireStation": "Fire Station",
            "PowerPlant": "Power Plant",
            "PowerLine": "Power Line"
        }

        self.item_descriptions = {
            # Tools & Nature
            "Axe": "Chops down trees to clear land for development.",
            "Hammer": "Demolishes buildings, roads, and rocks.\nRefunds part of the construction cost.",
            "Tree": "A natural forest tree.\nImproves the satisfaction of nearby residents.",
            "Rock": "A solid rock formation.\nMust be cleared with a Hammer to build here.",

            # Infrastructure
            "Road": "Public Road.\nEssential for citizens to commute to work and for zones to develop.",
            "PowerLine": "High-Voltage Transmission Line.\nTransmits electricity between non-contiguous areas.",

            # Zones
            "ResZone": "Residential Zone.\nCitizens will automatically build homes here if connected to a road.",
            "IndZone": "Industrial Zone.\nProvides jobs, but lowers the satisfaction of nearby residential areas.",
            "SerZone": "Service Zone.\nProvides jobs and helps balance out industrial production.",

            # Basic Service Buildings
            "Police": "Police Station.\nGuarantees public safety for fields within its radius.",
            "Stadium": "Stadium.\nProvides a massive satisfaction bonus to citizens living or working nearby.",

            # Advanced Service Buildings (Optional Features)
            "FireStation": "Fire Station.\nReduces fire risk in its radius and dispatches fire trucks to emergencies.",
            "School": "School.\nProvides secondary education, increasing citizen income and tax revenue.",
            "University": "University.\nProvides tertiary education for maximum citizen income and tax revenue.",
            "PowerPlant": "Power Plant.\nGenerates electricity. Must be adjacent to zones or connected via power lines."
        }

        # --- NEW: Improved Button Layout ---
        # 1. System Controls (Top Left)
        self.save_btn_rect = pg.Rect(20, 45, 110, 35)
        self.load_btn_rect = pg.Rect(140, 45, 110, 35)
        
        # 2. Financial Controls (Top Center-Left, further from System Controls)
        finance_start_x = 300
        self.tax_plus_rect = pg.Rect(finance_start_x, 45, 35, 35)
        self.tax_minus_rect = pg.Rect(finance_start_x + 45, 45, 35, 35)
        self.loan_btn_rect = pg.Rect(finance_start_x + 100, 45, 140, 35)
        self.repay_btn_rect = pg.Rect(finance_start_x + 250, 45, 140, 35)

        self.help_btn_rect = pg.Rect(20, self.height - 60, 110, 35)
        self.budget_btn_rect = pg.Rect(140, self.height - 60, 110, 35)
        self.music_btn_rect = pg.Rect(260, self.height - 60, 130, 35)
        self.show_help = False
        self.show_budget = False
        self.budget_scroll = 0

        # Main Menu Buttons
        self.play_btn_rect = pg.Rect((self.width - 250) // 2, self.height // 2 - 50, 250, 50)
        self.main_load_btn_rect = pg.Rect((self.width - 250) // 2, self.height // 2 + 20, 250, 50)

        # Game Over Buttons (Center of Screen)
        self.game_over_w, self.game_over_h = 600, 350
        self.game_over_rect = pg.Rect((self.width - self.game_over_w) // 2, (self.height - self.game_over_h) // 2, self.game_over_w, self.game_over_h)
        btn_y = self.game_over_rect.bottom - 80
        self.restart_btn_rect = pg.Rect(self.game_over_rect.x + 100, btn_y, 160, 45)
        self.load_save_btn_rect = pg.Rect(self.game_over_rect.right - 260, btn_y, 160, 45)

        self.menu_action = None
        self.game = None # Set by Game class

    @property
    def examined_tile(self):
        return self._examined_tile

    @examined_tile.setter
    def examined_tile(self, tile):
        """Cache the scaled image when a new tile is examined to save FPS."""
        self._examined_tile = tile
        if tile is not None:
            max_w = self.select_rect.width * .25
            max_h = self.select_rect.height * .6
            orig_w = tile.image.get_width()
            orig_h = tile.image.get_height()
            scale_w = max_w / orig_w
            scale_h = max_h / orig_h
            scale = min(scale_w, scale_h)
            final_w = int(orig_w * scale)
            final_h = int(orig_h * scale)
            self.examined_tile_scaled_img = pg.transform.smoothscale(tile.image, (final_w, final_h))
        else:
            self.examined_tile_scaled_img = None

    def create_build_hud(self):
        # 1. Grid Configuration
        cols = 3
        gap = 10
        menu_padding = 10
        item_padding = 10

        # 2. Count valid images and calculate how many rows we need
        valid_images = {k: v for k, v in self.images.items() if v.get_width() > 0}
        total_items = len(valid_images)
        rows = (total_items + cols - 1) // cols  # Math trick to always round up

        # 3. Calculate dynamic cell size based on the width
        available_width = self.build_rect.width - (menu_padding * 2) - (gap * (cols - 1))
        cell_w = available_width // cols
        cell_h = cell_w  # Keep slots square

        # 4. Calculate the EXACT height the menu needs to be to hold all rows
        total_height = (menu_padding * 2) + (rows * cell_h) + ((rows - 1) * gap)

        # 5. Resize and Reposition the menu box!
        self.build_rect.height = total_height
        self.build_rect.bottom = self.height - 20  # Anchor it 20px above the bottom edge
        self.build_rect.right = self.width - 20  # Anchor it 20px from the right edge

        # Recreate the grey background surface so it stretches to the new height
        self.build_surface = pg.Surface((self.build_rect.width, self.build_rect.height), pg.SRCALPHA)
        self.build_surface.fill(self.hud_colour)

        # Now start drawing from the newly calculated top-left corner
        start_x = self.build_rect.x + menu_padding
        start_y = self.build_rect.y + menu_padding

        tiles = []
        col, row = 0, 0

        for image_name, image in valid_images.items():
            # Apply 10px padding for every item in the grid
            max_img_w = cell_w - (item_padding * 2)
            max_img_h = cell_h - (item_padding * 2)

            orig_w, orig_h = image.get_size()
            scale = min(max_img_w / orig_w, max_img_h / orig_h)
            new_w, new_h = max(1, int(orig_w * scale)), max(1, int(orig_h * scale))

            image_scale = pg.transform.smoothscale(image, (new_w, new_h))

            # Calculate slot positions
            cell_x = start_x + (col * (cell_w + gap))
            cell_y = start_y + (row * (cell_h + gap))

            offset_x = (cell_w - new_w) // 2
            offset_y = (cell_h - new_h) // 2

            rect = image_scale.get_rect(topleft=(cell_x + offset_x, cell_y + offset_y))
            cell_rect = pg.Rect(cell_x, cell_y, cell_w, cell_h)

            item_type = "Tool" if image_name in ["Axe", "Hammer"] else "Building"
            w, h = BUILDING_SPECS.get(image_name, (1, 1))

            tiles.append({
                "name": image_name,
                "icon": image_scale,
                "image": image,
                "rect": rect,
                "cell_rect": cell_rect,
                "affordable": True,
                "type": item_type,
                "grid_width": w,
                "grid_height": h
            })

            col += 1
            if col >= cols:
                col, row = 0, row + 1

        return tiles

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        mouse_action = pg.mouse.get_pressed()
        mouse_clicked = mouse_action[0] and not self.mouse_pressed
        self.mouse_pressed = mouse_action[0]

        self.hovered_tile = None
        self.menu_action = None

        if mouse_clicked:
            if self.game and self.game.menu_state == "MAIN_MENU":
                if self.play_btn_rect.collidepoint(mouse_pos):
                    self.menu_action = "PLAY"
                elif self.main_load_btn_rect.collidepoint(mouse_pos):
                    self.menu_action = "MAIN_LOAD"
                elif hasattr(self, "music_btn_rect_main") and self.music_btn_rect_main.collidepoint(mouse_pos):
                    self.game.toggle_music()
                return

            if self.save_btn_rect.collidepoint(mouse_pos):
                self.menu_action = "SAVE"
                return
            elif self.load_btn_rect.collidepoint(mouse_pos):
                self.menu_action = "LOAD"
                return
            
            # Budget interactions
            elif self.tax_plus_rect.collidepoint(mouse_pos):
                self.resource_manager.tax_per_citizen += 1
                if self.game:
                    self.game.add_notification(f"TAX INCREASED: ${self.resource_manager.tax_per_citizen}", (255, 255, 100))
                    self.game.calculate_satisfaction_and_growth()
            elif self.tax_minus_rect.collidepoint(mouse_pos):
                if self.resource_manager.tax_per_citizen > 0:
                    self.resource_manager.tax_per_citizen -= 1
                    if self.game:
                        self.game.add_notification(f"TAX DECREASED: ${self.resource_manager.tax_per_citizen}", (100, 255, 255))
                        self.game.calculate_satisfaction_and_growth()
            elif self.loan_btn_rect.collidepoint(mouse_pos):
                self.resource_manager.take_loan(1000, self.game)
                if self.game: self.game.add_notification("LOAN TAKEN: +$1,000", (100, 255, 100))
                self.game.calculate_satisfaction_and_growth()
            elif self.repay_btn_rect.collidepoint(mouse_pos):
                if self.resource_manager.repay_loan(1000, self.game):
                    if self.game: self.game.add_notification("LOAN REPAID: -$1,000", (255, 215, 0))
                    self.game.calculate_satisfaction_and_growth()
                else:
                    if self.game: self.game.add_notification("NOT ENOUGH FUNDS OR NO LOAN", (255, 100, 100))
            elif self.help_btn_rect.collidepoint(mouse_pos):
                self.show_help = not self.show_help
                if self.show_help: self.show_budget = False
            elif self.budget_btn_rect.collidepoint(mouse_pos):
                self.show_budget = not self.show_budget
                if self.show_budget: self.show_help = False
            elif self.music_btn_rect.collidepoint(mouse_pos):
                if self.game:
                    self.game.toggle_music()
            
            # Game Over Interactions
            if self.resource_manager.is_mayor_replaced:
                if self.restart_btn_rect.collidepoint(mouse_pos):
                    self.menu_action = "RESTART"
                elif self.load_save_btn_rect.collidepoint(mouse_pos):
                    self.menu_action = "LOAD"

        # Right click deselects
        if mouse_action[2]:
            self.selected_tile = None

        for tile in self.tiles:
            tile["affordable"] = self.resource_manager.is_affordable(tile["name"])
            # Check if mouse is in the full cell area, not just the icon
            if tile["cell_rect"].collidepoint(mouse_pos):
                self.hovered_tile = tile
                if mouse_clicked and tile["affordable"]:
                    if self.selected_tile == tile:
                        self.selected_tile = None
                    else: self.selected_tile = tile
                    break

    def draw(self, screen, current_date=None, current_speed=1):
        # Draw HUD elements using their pre-calculated Rects
        screen.blit(self.resource_surface, self.resource_rect.topleft)
        screen.blit(self.build_surface, self.build_rect.topleft)

        # Select HUD
        if self.examined_tile is not None:
            screen.blit(self.select_surface, self.select_rect.topleft)

            # 1. Draw Title (Gold color)
            raw_name = self.examined_tile.name

            # Translate raw name to friendly name (defaults to raw name if not in dict)
            title_text = self.display_names.get(raw_name, raw_name)

            draw_text(screen, title_text, 35, (255, 215, 0), (self.select_rect.x + 15, self.select_rect.y + 10))

            # 2. Draw a clean dividing line
            pg.draw.line(screen, (255, 255, 255), (self.select_rect.x + 15, self.select_rect.y + 40),
                         (self.select_rect.right - 15, self.select_rect.y + 40))

            # 3. Blit the building/nature image
            img_x = self.select_rect.x + 15
            img_y = self.select_rect.y + 50
            screen.blit(self.examined_tile_scaled_img, (img_x, img_y))

            # 4. Draw the Description Text (Use raw_name to look up the description!)
            desc = self.item_descriptions.get(raw_name, "A structure in your city.")
            
            # Show occupancy/local satisfaction in description area for zones
            if hasattr(self.examined_tile, 'capacity'):
                # Moved to dedicated status section below to prevent description overflow
                pass

            desc_x = img_x + self.examined_tile_scaled_img.get_width() + 15
            desc_y = img_y

            # --- NEW: Dynamic Word Wrapping ---
            font = pg.font.SysFont(None, 20)
            max_text_width = self.select_rect.right - desc_x - 15  # 15px padding from the right edge

            wrapped_lines = []
            for paragraph in desc.split('\n'):
                words = paragraph.split(' ')
                current_line = ""
                for word in words:
                    test_line = current_line + word + " "
                    # Check if adding this word makes the line wider than our box
                    if font.size(test_line)[0] < max_text_width:
                        current_line = test_line
                    else:
                        wrapped_lines.append(current_line)
                        current_line = word + " "
                wrapped_lines.append(current_line)

            # Print multi-line text and track our Y-coordinate
            current_y = desc_y
            for line in wrapped_lines:
                draw_text(screen, line, 20, (220, 220, 220), (desc_x, current_y))
                current_y += 22  # Move down a line

            # --- 5. Show Status ---
            current_y += 10  # Add a little extra visual padding before the stats

            if hasattr(self.examined_tile, 'capacity'):
                cap = self.examined_tile.capacity
                occ = self.examined_tile.occupants
                percent = int((occ / cap) * 100) if cap > 0 else 0

                # Determine labels based on zone type
                is_working_zone = self.examined_tile.name in ["IndZone", "SerZone"]
                if is_working_zone:
                    pop_label = "Employees"
                elif self.examined_tile.name in ["School", "University"]:
                    pop_label = "Students"
                else:
                    pop_label = "Local Pop"

                # Draw Saturation
                status_text = f"{pop_label}: {occ}/{cap} ({percent}%)"
                draw_text(screen, status_text, 22, (200, 200, 255), (desc_x, current_y))
                current_y += 20

                # Draw Local Satisfaction (Only for Residential Zones or non-working buildings with capacity)
                if not is_working_zone and hasattr(self.examined_tile, 'local_satisfaction'):
                    sat = self.examined_tile.local_satisfaction
                    sat_text = f"Satisfaction: {sat}%"

                    # Color code it just like the top bar
                    if sat > 75:
                        sat_color = (100, 255, 100)  # Green
                    elif sat > 50:
                        sat_color = (255, 255, 100)  # Yellow
                    else:
                        sat_color = (255, 100, 100)  # Red

                    draw_text(screen, sat_text, 22, sat_color, (desc_x, current_y))
                    current_y += 20

                # Show active bonuses (limit to 4 to accommodate new global factors)
                if hasattr(self.examined_tile, 'bonuses') and self.examined_tile.bonuses:
                    for bonus in self.examined_tile.bonuses[:4]: # Show max 4 bonuses
                        draw_text(screen, f"• {bonus}", 18, (255, 255, 150), (desc_x, current_y))
                        current_y += 18
            if hasattr(self.examined_tile, 'get_age_formatted') and self.game:
                age_text = self.examined_tile.get_age_formatted(self.game.current_date)
                draw_text(screen, f"Age: {age_text}", 22, (150, 255, 150), (desc_x, current_y))
                current_y += 20
        for tile in self.tiles:
            # 1. Draw the slot background (Dark grey with rounded corners)
            pg.draw.rect(screen, (40, 40, 45, 200), tile["cell_rect"], border_radius=8)

            # 2. Draw a subtle border around the slot
            pg.draw.rect(screen, (90, 90, 100, 255), tile["cell_rect"], 2, border_radius=8)

            # 3. Draw the actual icon
            icon = tile["icon"].copy()
            if not tile["affordable"]:
                icon.set_alpha(100)  # Ghost it out if you can't afford it
            screen.blit(icon, tile["rect"].topleft)

            # 4. Draw interactive highlights (Hover & Selected states)
            if self.selected_tile == tile:
                # Bright green thick border if currently selected
                pg.draw.rect(screen, (100, 255, 100), tile["cell_rect"], 3, border_radius=8)
            elif self.hovered_tile == tile:
                # Gold border if the mouse is just hovering over it
                pg.draw.rect(screen, (255, 215, 0), tile["cell_rect"], 2, border_radius=8)

        # --- TOP BAR: CITY STATS ---
        # Positioned to the top right
        pos_x = self.width - 600

        # 1. Funds
        funds_text = f"Funds: ${int(self.resource_manager.funds):,}"
        # Make it red if funds are negative (operating on credit)
        funds_color = (255, 100, 100) if self.resource_manager.funds < 0 else (255, 255, 255)
        draw_text(screen, funds_text, 30, funds_color, (pos_x, 0))
        pos_x += 250

        # 2. Population
        pop_text = f"Pop: {int(self.resource_manager.population):,}"
        draw_text(screen, pop_text, 30, (255, 255, 255), (pos_x, 0))
        pos_x += 150

        # 3. Satisfaction
        sat = int(self.resource_manager.satisfaction)
        sat_text = f"Sat: {sat}%"
        # Color code satisfaction: Green (>75%), Yellow (50-75%), Red (<50%)
        if sat > 75:
            sat_color = (100, 255, 100)
        elif sat > 50:
            sat_color = (255, 255, 100)
        else:
            sat_color = (255, 100, 100)

        draw_text(screen, sat_text, 30, sat_color, (pos_x, 0))

        if current_date:
            date_str = current_date.strftime("%d %b %Y")
            time_text = f"{date_str}  |  Speed: {current_speed}x"
            draw_text(screen, time_text, 30, (255, 255, 255), (self.width // 2 - 350, 0))


        if self.hovered_tile is not None:
            self.draw_tooltip(screen, pg.mouse.get_pos(), self.hovered_tile)

        # --- TOP LEFT: SYSTEM & FINANCE BUTTONS ---
        mouse_pos = pg.mouse.get_pos()
        
        def draw_styled_button(rect, text, base_color=(60, 60, 70), hover_color=(90, 90, 110), border_color=(200, 200, 200), font_size=20):
            # Modern button with rounded corners and hover effect
            is_hovered = rect.collidepoint(mouse_pos)
            color = hover_color if is_hovered else base_color
            
            # Draw shadow for "3D" effect
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            pg.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=6)
            
            # Draw main button
            pg.draw.rect(screen, color, rect, border_radius=6)
            pg.draw.rect(screen, border_color, rect, 2, border_radius=6)
            
            # Draw text - Centered
            font = pg.font.SysFont("Trebuchet MS", font_size, bold=True)
            text_surf = font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)

        # 1. System Controls (Blueish Grey)
        sys_color = (50, 70, 90)
        sys_hover = (70, 90, 110)
        draw_styled_button(self.save_btn_rect, "SAVE", sys_color, sys_hover)
        draw_styled_button(self.load_btn_rect, "LOAD", sys_color, sys_hover)

        # 2. Tax Controls (Greenish Grey for Income)
        tax_color = (60, 90, 60)
        tax_hover = (80, 110, 80)
        draw_text(screen, f"Tax: ${self.resource_manager.tax_per_citizen}", 22, (255, 255, 255), (self.tax_plus_rect.x, 18))
        draw_styled_button(self.tax_plus_rect, "+", tax_color, tax_hover)
        draw_styled_button(self.tax_minus_rect, "-", tax_color, tax_hover)

        # 3. Loan Controls (Gold/Orange for Money management)
        loan_color_base = (110, 90, 50)
        loan_hover = (130, 110, 70)
        debt_label_color = (255, 200, 100) if self.resource_manager.total_loan_amount > 0 else (200, 200, 200)
        draw_text(screen, f"Debt: ${self.resource_manager.total_loan_amount:,}", 22, debt_label_color, (self.loan_btn_rect.x, 18))
        draw_styled_button(self.loan_btn_rect, "TAKE LOAN", loan_color_base, loan_hover)
        
        # Repay should be different color or highlighted if possible
        repay_color = (130, 60, 60) if self.resource_manager.total_loan_amount > 0 else (70, 70, 70)
        repay_hover = (150, 80, 80) if self.resource_manager.total_loan_amount > 0 else (90, 90, 90)
        draw_styled_button(self.repay_btn_rect, "REPAY LOAN", repay_color, repay_hover)

        # Help Button
        help_color = (90, 50, 90) if self.show_help else (70, 70, 80)
        help_hover = (110, 70, 110) if self.show_help else (90, 90, 100)
        draw_styled_button(self.help_btn_rect, "HELP", help_color, help_hover)

        # Budget Button
        budget_color = (50, 90, 90) if self.show_budget else (70, 70, 80)
        budget_hover = (70, 110, 110) if self.show_budget else (90, 90, 100)
        draw_styled_button(self.budget_btn_rect, "BUDGET", budget_color, budget_hover)

        # Music Button
        music_text = "MUSIC: ON" if (self.game and self.game.music_on) else "MUSIC: OFF"
        music_color = (60, 90, 60) if (self.game and self.game.music_on) else (130, 60, 60)
        music_hover = (80, 110, 80) if (self.game and self.game.music_on) else (150, 80, 80)
        draw_styled_button(self.music_btn_rect, music_text, music_color, music_hover)

        if self.show_help:
            self.draw_help_overlay(screen)
        
        if self.show_budget:
            self.draw_budget_panel(screen)

        if self.resource_manager.is_mayor_replaced:
            self.draw_game_over_panel(screen)

        # NEW: Education Status HUD (Bottom Left)
        res = self.resource_manager
        edu_y = self.height - 180
        draw_text(screen, "CITIZEN EDUCATION", 24, (255, 215, 0), (20, edu_y))

        draw_text(screen, f"Primary: {res.edu_primary}", 18, (200, 200, 200), (30, edu_y + 30))
        draw_text(screen, f"Secondary: {res.edu_secondary}", 18, (150, 255, 150), (30, edu_y + 50))
        draw_text(screen, f"Tertiary: {res.edu_tertiary}", 18, (150, 150, 255), (30, edu_y + 70))

        # Visual Progress Bar
        if res.population > 0:
            bar_w = 150
            pg.draw.rect(screen, (50, 50, 50), (30, edu_y + 95, bar_w, 10))
            sec_w = (res.edu_secondary / res.population) * bar_w
            tert_w = (res.edu_tertiary / res.population) * bar_w
            pg.draw.rect(screen, (100, 255, 100), (30, edu_y + 95, sec_w, 10))
            pg.draw.rect(screen, (100, 100, 255), (30 + sec_w, edu_y + 95, tert_w, 10))

    def draw_budget_panel(self, screen):
        # Semi-transparent overlay
        overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))

        # Panel dimensions
        panel_w, panel_h = 700, 500
        panel_x, panel_y = (self.width - panel_w) // 2, (self.height - panel_h) // 2
        panel_rect = pg.Rect(panel_x, panel_y, panel_w, panel_h)

        # Draw panel with shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pg.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=12)
        pg.draw.rect(screen, (45, 45, 55), panel_rect, border_radius=12)
        pg.draw.rect(screen, (200, 200, 200), panel_rect, 3, border_radius=12)

        # Title
        draw_text(screen, "CITY BUDGET REVIEW", 45, (255, 215, 0), (panel_x + 180, panel_y + 20))
        pg.draw.line(screen, (200, 200, 200), (panel_x + 30, panel_y + 70), (panel_x + panel_w - 30, panel_y + 70), 2)

        # Header
        header_y = panel_y + 85
        draw_text(screen, "TIMESTAMP", 22, (200, 200, 200), (panel_x + 30, header_y))
        draw_text(screen, "CATEGORY", 22, (200, 200, 200), (panel_x + 180, header_y))
        draw_text(screen, "INCOME", 22, (100, 255, 100), (panel_x + 320, header_y))
        draw_text(screen, "EXPENSES", 22, (255, 100, 100), (panel_x + 450, header_y))
        draw_text(screen, "BALANCE", 22, (255, 255, 255), (panel_x + 580, header_y))
        pg.draw.line(screen, (100, 100, 100), (panel_x + 30, header_y + 30), (panel_x + panel_w - 30, header_y + 30), 1)

        # History Entries (Scrollable)
        history = self.resource_manager.budget_history
        entry_h = 40
        visible_count = 8
        content_y = header_y + 40
        
        # Handle scrolling (mouse wheel)
        for event in pg.event.get(pg.MOUSEBUTTONDOWN):
            if event.button == 4: # Scroll Up
                self.budget_scroll = max(0, self.budget_scroll - 1)
            elif event.button == 5: # Scroll Down
                self.budget_scroll = min(max(0, len(history) - visible_count), self.budget_scroll + 1)
            # Re-post other mouse clicks so they aren't lost
            else:
                pg.event.post(event)

        if not history:
            draw_text(screen, "No financial history available yet.", 24, (150, 150, 150), (panel_x + 180, content_y + 50))
            draw_text(screen, "(Budget logic updates daily)", 18, (120, 120, 120), (panel_x + 175, content_y + 80))
        else:
            # Render visible entries
            start_idx = self.budget_scroll
            end_idx = min(len(history), start_idx + visible_count)
            
            for i in range(start_idx, end_idx):
                entry = history[i]
                row_y = content_y + (i - start_idx) * entry_h
                
                # Timestamp
                draw_text(screen, str(entry["time"]), 18, (200, 200, 200), (panel_x + 30, row_y + 10))
                # Category
                draw_text(screen, str(entry.get("category", "OTHER")), 18, (255, 255, 255), (panel_x + 180, row_y + 10))
                # Income
                draw_text(screen, f"${int(entry['income']):,}", 18, (150, 255, 150), (panel_x + 320, row_y + 10))
                # Expenses
                draw_text(screen, f"-${int(entry['expenses']):,}", 18, (255, 150, 150), (panel_x + 450, row_y + 10))
                # Balance
                bal = int(entry["balance"])
                bal_color = (100, 255, 100) if bal >= 0 else (255, 100, 100)
                bal_sign = "+" if bal >= 0 else ""
                draw_text(screen, f"{bal_sign}${bal:,}", 18, bal_color, (panel_x + 580, row_y + 10))
                
                # Zebra striping
                if i % 2 == 0:
                    row_surface = pg.Surface((panel_w - 60, entry_h), pg.SRCALPHA)
                    row_surface.fill((255, 255, 255, 15))
                    screen.blit(row_surface, (panel_x + 30, row_y))

        # Close instruction
        draw_text(screen, "Press ESC or click BUDGET again to close. Use Mouse Wheel to scroll.", 18, (200, 200, 200), (panel_x + 130, panel_y + panel_h - 30))

    def draw_main_menu(self, screen):
        # Draw a darkened overlay for the menu
        overlay = pg.Surface((self.width, self.height), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        # Title
        title_text = "CITY BUILDER by Wit"
        font_title = pg.font.SysFont("Trebuchet MS", 80, bold=True)
        title_surf = font_title.render(title_text, True, (255, 215, 0))
        title_rect = title_surf.get_rect(center=(self.width // 2, self.height // 2 - 180))
        screen.blit(title_surf, title_rect)

        # Styled Button helper
        mouse_pos = pg.mouse.get_pos()
        def draw_styled_button(rect, text, base_color=(60, 60, 70), hover_color=(90, 90, 110), border_color=(200, 200, 200), font_size=24):
            is_hovered = rect.collidepoint(mouse_pos)
            color = hover_color if is_hovered else base_color
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            pg.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=6)
            pg.draw.rect(screen, color, rect, border_radius=6)
            pg.draw.rect(screen, border_color, rect, 2, border_radius=6)
            font = pg.font.SysFont("Trebuchet MS", font_size, bold=True)
            text_surf = font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)

        draw_styled_button(self.play_btn_rect, "PLAY NEW GAME", (60, 90, 60), (80, 110, 80))
        draw_styled_button(self.main_load_btn_rect, "LOAD LAST SAVE", (50, 70, 90), (70, 90, 110))
        
        # Music Button in Main Menu
        music_text = "MUSIC: ON" if (self.game and self.game.music_on) else "MUSIC: OFF"
        music_color = (60, 90, 60) if (self.game and self.game.music_on) else (130, 60, 60)
        music_hover = (80, 110, 80) if (self.game and self.game.music_on) else (150, 80, 80)
        
        # Position music button below the load button
        music_btn_menu_rect = self.music_btn_rect.copy()
        music_btn_menu_rect.centerx = self.width // 2
        music_btn_menu_rect.top = self.main_load_btn_rect.bottom + 20
        
        # Update the rect for interaction if needed, or just draw it and use the original rect if it's moved
        # Let's update self.music_btn_rect if we are in main menu, but that's messy.
        # Better: draw_main_menu uses a specific rect, and update() also checks that rect if in MAIN_MENU.
        
        draw_styled_button(music_btn_menu_rect, music_text, music_color, music_hover)
        
        # For interaction to work with the current update logic, we should probably update the rect
        # But wait, I'll just change self.music_btn_rect's position when in MAIN_MENU if I want to reuse it.
        # Actually, let's just make sure update() knows where it is.
        self.music_btn_rect_main = music_btn_menu_rect

    def draw_game_over_panel(self, screen):
        # Semi-transparent overlay for game over
        s = pg.Surface((self.width, self.height), pg.SRCALPHA)
        s.fill((20, 0, 0, 180)) # Dark red tint
        screen.blit(s, (0,0))

        # Main panel
        pg.draw.rect(screen, (40, 20, 20), self.game_over_rect, border_radius=12)
        pg.draw.rect(screen, (255, 50, 50), self.game_over_rect, 3, border_radius=12)

        # "YOU ARE FIRED!" text
        draw_text(screen, "YOU ARE FIRED!", 50, (255, 50, 50), (self.game_over_rect.x + 135, self.game_over_rect.y + 50))
        draw_text(screen, "THE PEOPLE HAS REVOLTED", 28, (220, 220, 220), (self.game_over_rect.x + 125, self.game_over_rect.y + 110))

        # Statistics summary
        stats_y = self.game_over_rect.y + 160
        draw_text(screen, f"Final Population: {self.resource_manager.population}", 24, (200, 200, 200), (self.game_over_rect.x + 180, stats_y))
        draw_text(screen, f"Final Funds: ${self.resource_manager.funds:,}", 24, (200, 200, 200), (self.game_over_rect.x + 180, stats_y + 30))

        # Buttons
        mouse_pos = pg.mouse.get_pos()
        def draw_styled_button(rect, text, base_color=(60, 60, 70), hover_color=(90, 90, 110), border_color=(200, 200, 200), font_size=20):
            # Modern button with rounded corners and hover effect
            is_hovered = rect.collidepoint(mouse_pos)
            color = hover_color if is_hovered else base_color
            
            # Draw shadow for "3D" effect
            shadow_rect = rect.copy()
            shadow_rect.y += 2
            pg.draw.rect(screen, (20, 20, 20), shadow_rect, border_radius=6)
            
            # Draw main button
            pg.draw.rect(screen, color, rect, border_radius=6)
            pg.draw.rect(screen, border_color, rect, 2, border_radius=6)
            
            # Draw text - Centered
            font = pg.font.SysFont("Trebuchet MS", font_size, bold=True)
            text_surf = font.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)

        draw_styled_button(self.restart_btn_rect, "RESTART", (50, 90, 50), (70, 110, 70), (255, 255, 255))
        draw_styled_button(self.load_save_btn_rect, "LOAD SAVE", (50, 70, 90), (70, 90, 110), (255, 255, 255))

    def draw_help_overlay(self, screen):
        # Semi-transparent overlay for instructions
        help_w, help_h = 500, 450
        help_rect = pg.Rect((self.width - help_w) // 2, (self.height - help_h) // 2, help_w, help_h)
        
        # Create a semi-transparent surface
        s = pg.Surface((help_w, help_h), pg.SRCALPHA)
        s.fill((30, 30, 40, 240))
        screen.blit(s, help_rect.topleft)
        
        pg.draw.rect(screen, (255, 255, 255), help_rect, 2, border_radius=12)

        draw_text(screen, "CITY BUILDER - HOW TO PLAY", 35, (255, 215, 0), (help_rect.x + 60, help_rect.y + 20))
        pg.draw.line(screen, (255, 255, 255), (help_rect.x + 20, help_rect.y + 60), (help_rect.right - 20, help_rect.y + 60))

        instructions = [
            "• BUILD ROADS: Essential for zones and services.",
            "• ZONES: Citizens build on Residential, Industrial,",
            "  and Service zones ONLY if connected to roads.",
            "• SERVICES: Police/Stadiums provide bonuses if on roads.",
            "• SATISFACTION: Keep it high (>10%) to avoid being fired!",
            "• BUDGET: Taxes are collected annually. Don't stay in",
            "  debt for more than 5 years!",
            "• CONTROLS:",
            "  - L-Click: Select / Place / Examine building",
            "  - R-Click: Deselect tool / Close examine HUD",
            "  - SPACE: Pause game  |  1, 2, 3: Change Speed",
            "  - F5: Quick Save  |  F9: Quick Load"
        ]

        curr_y = help_rect.y + 80
        for line in instructions:
            draw_text(screen, line, 24, (220, 220, 220), (help_rect.x + 30, curr_y))
            curr_y += 28

        draw_text(screen, "Press HELP again to close", 20, (150, 150, 150), (help_rect.x + 150, help_rect.bottom - 30))

    def draw_tooltip(self, screen, mouse_pos, tile):
        raw_name = tile["name"]
        display_name = self.display_names.get(raw_name,raw_name)
        desc = self.item_descriptions.get(raw_name, "No description available.")

        # 1. Format the cost text
        cost = self.resource_manager.costs.get(raw_name, 0)
        if cost > 0:
            cost_text = f"Cost: ${cost:,}"
        else:
            cost_text = "Cost: Free"

        # 2. Setup fonts
        font_title = pg.font.SysFont(None, 30)
        font_desc = pg.font.SysFont(None, 24)

        # 3. Render text surfaces
        title_surf = font_title.render(display_name, True, (255, 255, 255))
        cost_surf = font_desc.render(cost_text, True, (255, 200, 0))  # Gold color for cost

        # Handle multi-line descriptions (split by \n)
        desc_lines = desc.split('\n')
        desc_surfs = [font_desc.render(line, True, (200, 200, 200)) for line in desc_lines]

        # 4. Calculate dynamic box dimensions based on the widest/tallest text
        max_text_width = max(title_surf.get_width(), cost_surf.get_width(), *(s.get_width() for s in desc_surfs))
        box_width = max_text_width + 20  # Add padding

        total_text_height = title_surf.get_height() + cost_surf.get_height() + sum(s.get_height() for s in desc_surfs)
        box_height = total_text_height + 30  # Add padding and line spacing

        # 5. Position the box (Offset to the top-left of the mouse so it doesn't cover the cursor)
        box_x = mouse_pos[0] - box_width - 15
        box_y = mouse_pos[1] - box_height - 15

        # Prevent the tooltip from going off the left/top edges of the screen
        if box_x < 0: box_x = mouse_pos[0] + 20
        if box_y < 0: box_y = mouse_pos[1] + 20

        # 6. Draw the background box and border
        tooltip_rect = pg.Rect(box_x, box_y, box_width, box_height)
        pg.draw.rect(screen, (30, 30, 30, 230), tooltip_rect)  # Dark gray background
        pg.draw.rect(screen, (255, 255, 255), tooltip_rect, 2)  # White border

        # 7. Blit the text surfaces onto the screen
        current_y = box_y + 10
        screen.blit(title_surf, (box_x + 10, current_y))
        current_y += title_surf.get_height() + 5

        for d_surf in desc_surfs:
            screen.blit(d_surf, (box_x + 10, current_y))
            current_y += d_surf.get_height() + 2

        current_y += 5
        screen.blit(cost_surf, (box_x + 10, current_y))

        # --- BOTTOM LEFT: HELP BUTTON & CONTROLS ---
        # Draw with a slight grey color so it isn't too distracting
        # Note: help_btn_rect is already handled in draw_styled_button
        pass

    """
    Crops invisible padding and forces flat tiles into a perfect 2:1 ration
    """
    @staticmethod
    def format_isometric_asset(image, is_flat=False, grid_w=1, grid_h=1):
        bounding_rect = image.get_bounding_rect()
        if bounding_rect.width == 0 or bounding_rect.height == 0:
            return image  # Failsafe for empty images

        cropped = image.subsurface(bounding_rect).copy()

        if is_flat:
            # In your engine, a 1x1 tile footprint is exactly 128x64.
            # A 2x2 tile footprint is exactly 256x128.
            target_w = (grid_w + grid_h) * 64
            target_h = (grid_w + grid_h) * 32
            return pg.transform.smoothscale(cropped, (target_w, target_h))

        # For tall 3D buildings, we ONLY crop the padding to fix depth sorting.
        # We do not squash them, or they would look like flat pancakes!
        return cropped

    @staticmethod
    def load_images():
        raw_images = {
            "Axe": pg.image.load(AXE_URL).convert_alpha(),
            "Hammer": pg.image.load(HAMMER_URL).convert_alpha(),
            "Tree": pg.image.load(TREE_URL).convert_alpha(),
            "ResZone": pg.image.load(RESZONE_URL1).convert_alpha(),
            "IndZone": pg.image.load(INDZONE_URL1).convert_alpha(),
            "SerZone": pg.image.load(SERZONE_URL1).convert_alpha(),
            "Stadium": pg.image.load(STADIUM_URL).convert_alpha(),
            "University": pg.image.load(UNIVERSITY_URL).convert_alpha(),
            "School": pg.image.load(SCHOOL_URL).convert_alpha(),
            "FireStation": pg.image.load(FIRE_STATION_URL).convert_alpha(),
            "Police": pg.image.load(POLICE_URL).convert_alpha(),
            "PowerPlant": pg.image.load(POWERPLANT_URL).convert_alpha(),
            "Road": pg.image.load(ROAD_URL).convert_alpha(),
            "PowerLine": pg.image.load(POWERLINE_URL).convert_alpha(),
        }
        formatted_images = {}
        for name, img in raw_images.items():
            if name in ["Axe", "Hammer"]:
                formatted_images[name] = img
                continue
            is_flat_zone = name in ["ResZone", "IndZone", "SerZone"]
            w,h = BUILDING_SPECS.get(name, (1,1))
            formatted_images[name] = Hud.format_isometric_asset(img, is_flat=is_flat_zone, grid_w=w, grid_h=h)
        return formatted_images

    @staticmethod
    def scale_image(image, w=None, h=None):
        # Pythonic way to check for None
        if w is None and h is None:
            return image

        if h is None:
            scale = w / image.get_width()
            h = scale * image.get_height()
        elif w is None:
            scale = h / image.get_height()
            w = scale * image.get_width()

        # smoothscale generally yields better visual results than standard scale
        return pg.transform.smoothscale(image, (int(w), int(h)))