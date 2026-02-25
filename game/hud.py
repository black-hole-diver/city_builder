import pygame as pg

from .setting import *
from .utils import draw_text

class Hud:
    def __init__(self, resource_manager, width, height):
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
        self.select_surface = pg.Surface((width * 0.3, height * 0.2), pg.SRCALPHA)
        self.select_rect = self.select_surface.get_rect(topleft=(self.width * 0.35, self.height * 0.79))
        self.select_surface.fill(self.hud_colour)

        self.images = self.load_images()
        self.tiles = self.create_build_hud()

        self.selected_tile = None

        # Internal variables for caching the examined tile's scaled image
        self._examined_tile = None
        self.examined_tile_scaled_img = None

        self.hovered_tile = None
        self.mouse_pressed = False

        self.item_descriptions = {
            "Axe": "Chops down trees.\nGrants 5 wood.",
            "Hammer": "Demolishes buildings & rocks.\nGrants 5 stone.",
            "Lumbermill": "Produces 1 wood\nevery 2 seconds.",
            "Stonemasonry": "Produces 1 stone\nevery 2 seconds.",
            "ResZone": "Apartment complex for the residents",
            "Tree": "A natural forest tree.\nUse an Axe to harvest 5 Wood.",
            "Rock": "A solid rock formation.\nUse a Hammer to harvest 5 Stone.",
            "Stadium": "Hosts massive events.\nIncreases happiness and clout."
        }

        self.save_btn_rect = pg.Rect(10,40,100,30)
        self.load_btn_rect = pg.Rect(120,40,100,30)
        self.menu_action = None

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
        # Use existing rect properties instead of recalculating
        start_x = self.build_rect.x + 10
        render_x = self.build_rect.x + 10
        render_y = self.build_rect.y + 10
        object_width = self.build_rect.width // 5

        tiles = []

        for image_name, image in self.images.items():
            # pg.transform.scale creates a new surface, so .copy() is unnecessary
            image_scale = self.scale_image(image, w=object_width)

            if render_x + image_scale.get_width() > self.build_rect.right - 10:
                render_x = start_x
                render_y += image_scale.get_height() + 10

            rect = image_scale.get_rect(topleft=(render_x, render_y))

            item_type = "Tool" if image_name in ["Axe", "Hammer"] else "Building"
            w,h = 1,1
            if image_name == "ResZone":
                w,h = 4,4
            if image_name == "Stadium":
                w,h = 6,6

            tiles.append(
                {
                    "name": image_name,
                    "icon": image_scale,
                    "image": image,
                    "rect": rect,
                    "affordable": True,
                    "type": item_type,
                    "grid_width": w,
                    "grid_height": h
                }
            )

            render_x += image_scale.get_width() + 10

        return tiles

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        mouse_action = pg.mouse.get_pressed()
        mouse_clicked = mouse_action[0] and not self.mouse_pressed
        self.mouse_pressed = mouse_action[0]

        self.hovered_tile = None
        self.menu_action = None

        if mouse_clicked:
            if self.save_btn_rect.collidepoint(mouse_pos):
                self.menu_action = "SAVE"
                return
            elif self.load_btn_rect.collidepoint(mouse_pos):
                self.menu_action = "LOAD"
                return

        # Right click deselects
        if mouse_action[2]:
            self.selected_tile = None

        for tile in self.tiles:
            tile["affordable"] = self.resource_manager.is_affordable(tile["name"])
            if tile["rect"].collidepoint(mouse_pos):
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
            title_text = self.examined_tile.name
            draw_text(screen, title_text, 35, (255, 215, 0), (self.select_rect.x + 15, self.select_rect.y + 10))

            # 2. Draw a clean dividing line
            pg.draw.line(screen, (255, 255, 255), (self.select_rect.x + 15, self.select_rect.y + 40),
                         (self.select_rect.right - 15, self.select_rect.y + 40))

            # 3. Blit the building/nature image
            img_x = self.select_rect.x + 15
            img_y = self.select_rect.y + 50
            screen.blit(self.examined_tile_scaled_img, (img_x, img_y))

            # 4. Draw the Description Text
            desc = self.item_descriptions.get(title_text, "A structure in your city.")
            desc_x = img_x + self.examined_tile_scaled_img.get_width() + 15
            desc_y = img_y

            # Print multi-line text cleanly
            for i, line in enumerate(desc.split('\n')):
                draw_text(screen, line, 22, (220, 220, 220), (desc_x, desc_y + (i * 25)))

            # 5. Show Status (Only applies to active buildings with a cooldown)
            if hasattr(self.examined_tile, 'resource_cooldown'):
                draw_text(screen, "Status: Operational", 22, (100, 255, 100), (desc_x, desc_y + 60))

            # # Blit the pre-scaled image instead of scaling it every frame
            # screen.blit(self.examined_tile_scaled_img, (self.select_rect.x + 10, self.select_rect.y + 40))
            #
            # draw_text(screen, self.examined_tile.name, 40, (255, 255, 255), self.select_rect.topleft)

        for tile in self.tiles:
            icon = tile["icon"].copy()
            if not tile["affordable"]: icon.set_alpha(100)
            screen.blit(icon, tile["rect"].topleft)

        # Resource text
        pos_x = self.width - 400

        for resource, resource_value in self.resource_manager.resources.items():
            text = resource + ": " + str(resource_value)
            draw_text(screen, text, 30, (255, 255, 255), (pos_x, 0))
            pos_x += 100

        if current_date:
            date_str = current_date.strftime("%d %b %Y")
            time_text = f"{date_str}  |  Speed: {current_speed}x"
            draw_text(screen, time_text, 30, (255, 255, 255), (self.width // 2 - 350, 0))


        if self.hovered_tile is not None:
            self.draw_tooltip(screen, pg.mouse.get_pos(), self.hovered_tile)

        pg.draw.rect(screen, (70, 70, 70), self.save_btn_rect)
        pg.draw.rect(screen, (255, 255, 255), self.save_btn_rect, 2)
        draw_text(screen, "SAVE", 24, (255, 255, 255), (self.save_btn_rect.x + 25, self.save_btn_rect.y + 8))

        pg.draw.rect(screen, (70, 70, 70), self.load_btn_rect)
        pg.draw.rect(screen, (255, 255, 255), self.load_btn_rect, 2)
        draw_text(screen, "LOAD", 24, (255, 255, 255), (self.load_btn_rect.x + 25, self.load_btn_rect.y + 8))

    def draw_tooltip(self, screen, mouse_pos, tile):
        name = tile["name"]
        desc = self.item_descriptions.get(name, "No description available.")

        # 1. Format the cost text
        costs = self.resource_manager.costs.get(name, {})
        if costs:
            cost_text = "Cost: " + ", ".join(f"{v} {k}" for k, v in costs.items())
        else:
            cost_text = "Cost: Free"

        # 2. Setup fonts
        font_title = pg.font.SysFont(None, 30)
        font_desc = pg.font.SysFont(None, 24)

        # 3. Render text surfaces
        title_surf = font_title.render(name, True, (255, 255, 255))
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

    @staticmethod
    def load_images():
        images = {
            "Lumbermill": pg.image.load(BUILDING1_URL).convert_alpha(),
            "Stonemasonry": pg.image.load(BUILDING2_URL).convert_alpha(),
            "Axe": pg.image.load(AXE_URL).convert_alpha(),
            "Hammer": pg.image.load(HAMMER_URL).convert_alpha(),
            "ResZone": pg.image.load(RESZONE_URL).convert_alpha(),
            "Stadium": pg.image.load(STADIUM_URL).convert_alpha()
        }
        return images

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