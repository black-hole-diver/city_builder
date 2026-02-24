import pygame as pg
import random
import noise
from .setting import TILE_SIZE
from .workers import Worker
from .buildings import Lumbermill, Stonemasonry, Building
from .tools import Axe, Hammer
from typing import List, Optional

class World:
    def __init__(self, resource_manager, entities, hud, grid_length_x, grid_length_y, width, height):
        self.game_paused = False
        self.resource_manager = resource_manager
        self.entities = entities
        self.hud = hud
        self.grid_length_x = grid_length_x
        self.grid_length_y = grid_length_y
        self.width = width
        self.height = height

        self.perlin_scale = grid_length_x / 2

        # Create the base surface for the terrain
        self.grass_tiles = pg.Surface(
            (grid_length_x * TILE_SIZE * 2, grid_length_y * TILE_SIZE + 2 * TILE_SIZE),
            flags=pg.SRCALPHA
        ).convert_alpha()
        self.grass_tiles.fill((0,0,0,0))

        self.tiles = self.load_images()
        self.world = self.create_world()
        self.collision_matrix = self.create_collision_matrix()

        self.buildings: List[List[Optional['Building']]] = [[None for _ in range(self.grid_length_x)] for _ in range(self.grid_length_y)]
        self.workers: List[List[Optional['Worker']]] = [[None for _ in range(self.grid_length_x)] for _ in
                                                            range(self.grid_length_y)]

        self.temp_tile = None
        self.examine_tile = None

        # NEW: Cache the mask outline so we don't recalculate it 60 times a second
        self.examine_mask_points = None

        # Map string names to classes for cleaner building instantiation
        self.building_types = {
            "Lumbermill": Lumbermill,
            "Stonemasonry": Stonemasonry
        }

        self.tools = {
            "Axe": Axe(),
            "Hammer": Hammer()
        }

    def update(self, camera, game_paused):
        self.game_paused = game_paused
        mouse_pos = pg.mouse.get_pos()
        mouse_action = pg.mouse.get_pressed()

        # Right click to deselect
        if mouse_action[2]:
            self.examine_tile = None
            self.hud.examined_tile = None
            self.examine_mask_points = None

        self.temp_tile = None
        grid_pos = self.mouse_to_grid(mouse_pos[0], mouse_pos[1], camera.scroll)

        if self.hud.selected_tile is not None:
            if self.can_place_tile(grid_pos):
                img = self.hud.selected_tile["image"].copy()
                img.set_alpha(100)

                # Extract grid cell data once
                cell = self.world[grid_pos[0]][grid_pos[1]]
                render_pos = cell["render_pos"]
                iso_poly = cell["iso_poly"]
                collision = cell["collision"]
                selected_name = self.hud.selected_tile["name"]

                # if selected_name == "Axe":
                #     can_chop = (cell["tile"] == "tree")
                #     self.temp_tile = {
                #         "image": img,
                #         "render_pos": render_pos,
                #         "iso_poly": iso_poly,
                #         "collision": not can_chop,
                #     }
                #
                #     if mouse_action[0] and can_chop and not self.game_paused:
                #         self.world[grid_pos[0]][grid_pos[1]]["tile"] = ""
                #         self.world[grid_pos[0]][grid_pos[1]]["collision"] = False
                #         self.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
                #         self.resource_manager.resources["wood"] += 5
                # elif selected_name == "Hammer":
                #     has_building = self.buildings[grid_pos[0]][grid_pos[1]] is not None
                #     is_rock = cell["tile"] == "rock"
                #     can_demolish = has_building or is_rock
                #     self.temp_tile = {
                #         "image": img,
                #         "render_pos": render_pos,
                #         "iso_poly": iso_poly,
                #         "collision": not can_demolish
                #     }
                #     if mouse_action[0] and can_demolish and not self.game_paused:
                #         if has_building:
                #             building_to_remove = self.buildings[grid_pos[0]][grid_pos[1]]
                #             if building_to_remove in self.entities:
                #                 self.entities.remove(building_to_remove)
                #             self.buildings[grid_pos[0]][grid_pos[1]] = None
                #             if self.examine_tile == (grid_pos[0], grid_pos[1]):
                #                 self.examine_tile = None
                #                 self.hud.examined_tile = None
                #                 self.examine_mask_points = None
                #         elif is_rock:
                #             self.world[grid_pos[0]][grid_pos[1]]["tile"] = ""
                #             self.resource_manager.resources["stone"] += 5
                #         self.world[grid_pos[0]][grid_pos[1]]["collision"] = False
                #         self.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
                if selected_name in self.tools:
                    tool = self.tools[selected_name]
                    can_use = tool.can_use(grid_pos, self)
                    self.temp_tile = {
                        "image": img,
                        "render_pos": render_pos,
                        "iso_poly": iso_poly,
                        "collision": not can_use
                    }
                    if mouse_action[0] and can_use and not self.game_paused:
                        tool.use(grid_pos, self)
                else:
                    self.temp_tile = {
                        "image": img,
                        "render_pos": render_pos,
                        "iso_poly": iso_poly,
                        "collision": collision
                    }

                    # Place building
                    if mouse_action[0] and not collision and not self.game_paused:
                        building_name = self.hud.selected_tile["name"]
                        building_class = self.building_types.get(building_name)

                        if building_class:
                            building_image = self.hud.selected_tile["image"]
                            ent = building_class(render_pos, building_image, self.resource_manager)
                            self.entities.append(ent)
                            self.buildings[grid_pos[0]][grid_pos[1]] = ent
                            self.world[grid_pos[0]][grid_pos[1]]["collision"] = True
                            self.collision_matrix[grid_pos[1]][grid_pos[0]] = 0
                        self.hud.selected_tile = None

        else:
            if self.can_place_tile(grid_pos):
                building = self.buildings[grid_pos[0]][grid_pos[1]]
                # Select building to examine
                if mouse_action[0] and (building is not None):
                    self.examine_tile = (grid_pos[0], grid_pos[1])
                    self.hud.examined_tile = building
                    # Calculate the mask outline exactly ONCE upon clicking
                    self.examine_mask_points = pg.mask.from_surface(building.image).outline()

    def draw(self, screen, camera):
        screen.blit(self.grass_tiles, (camera.scroll.x, camera.scroll.y))

        # Pre-calculate global offsets outside the tight loop to save CPU cycles
        offset_x = self.grass_tiles.get_width() / 2 + camera.scroll.x
        offset_y = camera.scroll.y

        for x in range(self.grid_length_x):
            for y in range(self.grid_length_y):
                render_pos = self.world[x][y]["render_pos"]

                # Calculate final screen coordinates for this specific tile
                screen_x = render_pos[0] + offset_x

                # Draw world tiles
                tile_key = self.world[x][y]["tile"]
                if tile_key != "":
                    tile_img = self.tiles[tile_key]
                    screen_y = render_pos[1] - (tile_img.get_height() - TILE_SIZE) + offset_y
                    screen.blit(tile_img, (screen_x, screen_y))

                # Draw buildings
                building = self.buildings[x][y]
                if building is not None:
                    b_screen_y = render_pos[1] - (building.image.get_height() - TILE_SIZE) + offset_y
                    screen.blit(building.image, (screen_x, b_screen_y))

                    # Draw highlight mask using the cached points
                    if self.examine_tile == (x, y) and self.examine_mask_points:
                        mask_poly = [(mx + screen_x, my + b_screen_y) for mx, my in self.examine_mask_points]
                        pg.draw.polygon(screen, (255, 255, 255), mask_poly, 3)

                # Draw workers
                worker = self.workers[x][y]
                if worker is not None:
                    screen.blit(worker.image,(
                        render_pos[0] + offset_x, render_pos[1] - (worker.image.get_height() - TILE_SIZE) + offset_y,
                    ))

        # Draw "Ghost" Temp Tile
        if self.temp_tile is not None:
            iso_poly = self.temp_tile["iso_poly"]
            shifted_poly = [(px + offset_x, py + offset_y) for px, py in iso_poly]

            color = (255, 0, 0) if self.temp_tile["collision"] else (255, 255, 255)
            pg.draw.polygon(screen, color, shifted_poly, 3)

            render_pos = self.temp_tile["render_pos"]
            img = self.temp_tile["image"]
            screen_y = render_pos[1] - (img.get_height() - TILE_SIZE) + offset_y

            screen.blit(img, (render_pos[0] + offset_x, screen_y))

    def create_world(self):
        world = []
        # Calculate this offset once
        center_offset_x = self.grass_tiles.get_width() / 2

        for grid_x in range(self.grid_length_x):
            world.append([])
            for grid_y in range(self.grid_length_y):
                world_tile = self.grid_to_world(grid_x, grid_y)
                world[grid_x].append(world_tile)

                render_pos = world_tile["render_pos"]
                self.grass_tiles.blit(
                    self.tiles["block"],
                    (render_pos[0] + center_offset_x, render_pos[1])
                )

        return world

    def grid_to_world(self, grid_x, grid_y):
        rect = [
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE),
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE)
        ]

        iso_poly = [self.cart_to_iso(x, y) for x, y in rect]

        # Generator expressions are faster and use less memory than list comprehensions here
        minx = min(x for x, y in iso_poly)
        miny = min(y for x, y in iso_poly)

        r = random.randint(1, 100)
        perlin = 100 * noise.pnoise2(grid_x / self.perlin_scale, grid_y / self.perlin_scale)

        if perlin >= 15 or perlin <= -35:
            tile = "tree"
        else:
            if r == 1:
                tile = "tree"
            elif r == 2:
                tile = "rock"
            else:
                tile = ""

        return {
            "grid": [grid_x, grid_y],
            "cart_rect": rect,
            "iso_poly": iso_poly,
            "render_pos": [minx, miny],
            "tile": tile,
            "collision": tile != ""  # Simplified boolean logic
        }

    def create_collision_matrix(self):
        collision_matrix = [[1 for _ in range(self.grid_length_x)] for _ in range(self.grid_length_y)]
        for grid_x in range(self.grid_length_x):
            for grid_y in range(self.grid_length_y):
                if self.world[grid_x][grid_y]["collision"]:
                    collision_matrix[grid_y][grid_x] = 0
        return collision_matrix

    @staticmethod
    def cart_to_iso( x, y):
        iso_x = x - y
        iso_y = (x + y) / 2
        return iso_x, iso_y

    def mouse_to_grid(self, x, y, scroll):
        world_x = x - scroll.x - self.grass_tiles.get_width() / 2
        world_y = y - scroll.y
        cart_y = (2 * world_y - world_x) / 2
        cart_x = cart_y + world_x
        grid_x = int(cart_x // TILE_SIZE)
        grid_y = int(cart_y // TILE_SIZE)
        return grid_x, grid_y

    @staticmethod
    def load_images():
        return {
            "building1": pg.image.load("assets/graphics/building1.png").convert_alpha(),
            "building2": pg.image.load("assets/graphics/building2.png").convert_alpha(),
            "tree": pg.image.load("assets/graphics/tree.png").convert_alpha(),
            "rock": pg.image.load("assets/graphics/rock.png").convert_alpha(),
            "block": pg.image.load("assets/graphics/block.png").convert_alpha()
        }

    def can_place_tile(self, grid_pos):
        mouse_pos = pg.mouse.get_pos()

        # Check HUD panels using any() for cleaner, short-circuit logic
        hud_rects = [self.hud.resource_rect, self.hud.build_rect, self.hud.select_rect]
        if any(rect.collidepoint(mouse_pos) for rect in hud_rects):
            return False

        # BUG FIX: changed `self.grid_length_x` to `self.grid_length_y` for the Y axis check
        world_bounds = (0 <= grid_pos[0] < self.grid_length_x) and (0 <= grid_pos[1] < self.grid_length_y)
        return world_bounds