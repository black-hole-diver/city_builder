import pygame as pg
from .utils import draw_text


class Hud:
    def __init__(self, resource_manager, width, height):
        self.resource_manager = resource_manager
        self.width = width
        self.height = height
        self.hud_colour = (198, 155, 93, 175)

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

    @property
    def examined_tile(self):
        return self._examined_tile

    @examined_tile.setter
    def examined_tile(self, tile):
        """Cache the scaled image when a new tile is examined to save FPS."""
        self._examined_tile = tile
        if tile is not None:
            h = self.select_rect.height
            self.examined_tile_scaled_img = self.scale_image(tile.image, h=h * 0.7)
        else:
            self.examined_tile_scaled_img = None

    def create_build_hud(self):
        # Use existing rect properties instead of recalculating
        render_x = self.build_rect.x + 10
        render_y = self.build_rect.y + 10
        object_width = self.build_rect.width // 5

        tiles = []

        for image_name, image in self.images.items():
            # pg.transform.scale creates a new surface, so .copy() is unnecessary
            image_scale = self.scale_image(image, w=object_width)
            rect = image_scale.get_rect(topleft=(render_x, render_y))

            tiles.append(
                {
                    "name": image_name,
                    "icon": image_scale,
                    "image": image,
                    "rect": rect,
                    "affordable": True
                }
            )

            render_x += image_scale.get_width() + 10

        return tiles

    def update(self):
        mouse_pos = pg.mouse.get_pos()
        mouse_action = pg.mouse.get_pressed()

        # Right click deselects
        if mouse_action[2]:
            self.selected_tile = None

        # Left click selects
        if mouse_action[0]:
            for tile in self.tiles:
                if self.resource_manager.is_affordable(tile["name"]):
                    tile["affordable"] = True
                else:
                    tile["affordable"] = False
                if tile["rect"].collidepoint(mouse_pos) and tile["affordable"]:
                    self.selected_tile = tile
                    break  # Stop checking once we find a collision

    def draw(self, screen):
        # Draw HUD elements using their pre-calculated Rects
        screen.blit(self.resource_surface, self.resource_rect.topleft)
        screen.blit(self.build_surface, self.build_rect.topleft)

        # Select HUD
        if self.examined_tile is not None:
            screen.blit(self.select_surface, self.select_rect.topleft)

            # Blit the pre-scaled image instead of scaling it every frame
            screen.blit(self.examined_tile_scaled_img, (self.select_rect.x + 10, self.select_rect.y + 40))

            draw_text(screen, self.examined_tile.name, 40, (255, 255, 255), self.select_rect.topleft)

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

    @staticmethod
    def load_images():
        images = {
            "Lumbermill": pg.image.load("assets/graphics/building1.png").convert_alpha(),
            "Stonemasonry": pg.image.load("assets/graphics/building2.png").convert_alpha()
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