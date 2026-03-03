import pygame as pg
import random
import noise

from game.event_bus import EventBus
from .setting import (
    TILE_SIZE,
    FIRE_SPREAD_TIME,
    FIRE_STATION_RADIUS,
    CHANCE,
    BUILDING_REFUND_PERCENT,
    ZONE_REFUND_PERCENT,
    BLOCK_URL,
    TREE_URL,
    ROCK_URL,
)
from .workers import Worker
from .buildings import (
    Building,
    Tree,
    Zone,
    ResZone,
    IndZone,
    SerZone,
    Stadium,
    Police,
    FireStation,
    School,
    University,
    PowerPlant,
    Road,
    PowerLine,
)
from .tools import Axe, Hammer, VIP
from typing import List, Optional


class Scenery:
    def __init__(self, name, image):
        self.name = name.capitalize()
        self.image = image
        self.origin = None


class World:
    def __init__(
        self, game, resource_manager, entities, hud, grid_length_x, grid_length_y, width, height
    ):
        self.game = game
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
            flags=pg.SRCALPHA,
        ).convert_alpha()
        self.grass_tiles.fill((0, 0, 0, 0))

        self.tiles = self.load_images()
        self.world = self.create_world()
        self.collision_matrix = self.create_collision_matrix()

        self.fire_images = []
        self.fire_current_frame = 0
        self.fire_frame_timer = pg.time.get_ticks()

        try:
            for i in range(24):
                filename = f"assets/graphics/Fire/frame_{i:02d}_delay-0.08s.png"
                img = pg.image.load(filename).convert_alpha()
                target_width = 256
                scale_factor = target_width / img.get_width()
                target_height = int(img.get_height() * scale_factor)
                img = pg.transform.smoothscale(img, (target_width, target_height))
                self.fire_images.append(img)
        except Exception as e:
            print(f"Warning: Could not load fire animation image: {e}")

        self.buildings: List[List[Optional["Building"]]] = [
            [None for _ in range(self.grid_length_y)] for _ in range(self.grid_length_x)
        ]
        self.workers: List[List[Optional["Worker"]]] = [
            [None for _ in range(self.grid_length_y)] for _ in range(self.grid_length_x)
        ]

        self.temp_tile = None
        self.examine_tile = None

        # NEW: Cache the mask outline so we don't recalculate it 60 times a second
        self.examine_mask_points = None

        # Map string names to classes for cleaner building instantiation
        self.building_types = {
            "ResZone": ResZone,
            "IndZone": IndZone,
            "SerZone": SerZone,
            "Stadium": Stadium,
            "Police": Police,
            "FireStation": FireStation,
            "School": School,
            "University": University,
            "PowerPlant": PowerPlant,
            "Road": Road,
            "PowerLine": PowerLine,
            "Tree": Tree,
        }

        self.tools = {"Axe": Axe(), "Hammer": Hammer(), "VIP": VIP()}

        for gx in range(self.grid_length_x):
            for gy in range(self.grid_length_y):
                if self.world[gx][gy]["tile"] == "tree":
                    self.world[gx][gy]["tile"] = ""  # Remove scenery
                    render_pos = self.world[gx][gy]["render_pos"]
                    tree = Tree(
                        render_pos,
                        self.tiles["tree"],
                        self.resource_manager,
                        (gx, gy),
                        is_old_tree=True,
                    )
                    tree.game = self.game
                    self.entities.append(tree)
                    self.buildings[gx][gy] = tree
                    self.world[gx][gy]["collision"] = True
                    self.collision_matrix[gy][gx] = 0

    def update(self, camera, game_paused):
        self.game_paused = game_paused

        if self.fire_images:
            now = pg.time.get_ticks()
            if now - self.fire_frame_timer > 80:
                self.fire_current_frame = (self.fire_current_frame + 1) % len(self.fire_images)
                self.fire_frame_timer = now

        if not self.game_paused:
            self.process_fires()

        mouse_pos = pg.mouse.get_pos()
        mouse_action = pg.mouse.get_pressed()

        if getattr(self, "ignore_clicks_until_release", False):
            if not mouse_action[0]:
                self.ignore_clicks_until_release = False
            else:
                mouse_action = (False, mouse_action[1], mouse_action[2])

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
                # collision = cell["collision"]
                selected_name = self.hud.selected_tile["name"]

                if selected_name in self.tools:
                    tool = self.tools[selected_name]
                    can_use = tool.can_use(grid_pos, self)
                    self.temp_tile = {
                        "image": img,
                        "render_pos": render_pos,
                        "iso_poly": iso_poly,
                        "collision": not can_use,
                    }
                    if mouse_action[0] and can_use and not self.game_paused:
                        tool.use(grid_pos, self)
                else:
                    b_width = self.hud.selected_tile.get("grid_width", 1)
                    b_height = self.hud.selected_tile.get("grid_height", 1)
                    can_build = self.is_area_free(grid_pos[0], grid_pos[1], b_width, b_height)

                    cart_x = grid_pos[0] * TILE_SIZE
                    cart_y = grid_pos[1] * TILE_SIZE

                    multi_rect = [
                        (cart_x, cart_y),
                        (cart_x + b_width * TILE_SIZE, cart_y),
                        (cart_x + b_width * TILE_SIZE, cart_y + b_height * TILE_SIZE),
                        (cart_x, cart_y + b_height * TILE_SIZE),
                    ]

                    multi_iso_poly = [self.cart_to_iso(x, y) for x, y in multi_rect]

                    minx = min(px for px, py in multi_iso_poly)
                    miny = min(py for px, py in multi_iso_poly)

                    self.temp_tile = {
                        "image": img,
                        "render_pos": (minx, miny),
                        "iso_poly": multi_iso_poly,
                        "collision": not can_build,
                        "b_w": b_width,
                        "b_h": b_height,
                    }

                    # Place building
                    if mouse_action[0] and not self.temp_tile["collision"] and not self.game_paused:
                        building_name = self.hud.selected_tile["name"]
                        building_class = self.building_types.get(building_name)

                        if building_class:
                            building_image = self.hud.selected_tile["image"]
                            kwargs = {}
                            if building_name == "Tree":
                                kwargs["plant_date"] = self.game.current_date
                            ent = building_class(
                                (minx, miny),
                                building_image,
                                self.resource_manager,
                                grid_pos,
                                **kwargs,
                            )
                            ent.game = self.game  # Set game reference
                            self.resource_manager.apply_cost_to_resource(building_name, self.game)
                            EventBus.publish("play_sound", "creation")

                            # Update initial road access
                            ent.has_road_access = self.has_road_access(
                                grid_pos[0], grid_pos[1], b_width, b_height
                            )

                            self.entities.append(ent)
                            for x in range(grid_pos[0], grid_pos[0] + b_width):
                                for y in range(grid_pos[1], grid_pos[1] + b_height):
                                    self.buildings[x][y] = ent
                                    self.world[x][y]["collision"] = True
                                    self.collision_matrix[y][x] = 0

                            # NEW: Update road access for ALL buildings if we just placed a road
                            if building_name == "Road":
                                for e in self.entities:
                                    if hasattr(e, "has_road_access"):
                                        e.has_road_access = self.has_road_access(
                                            e.origin[0], e.origin[1], e.grid_width, e.grid_height
                                        )
                                # Recalculate satisfaction immediately for better responsiveness
                                EventBus.publish("recalculate_satisfaction")

                            # NEW: Instant Power Recalculation Trigger
                            power_conductors = [
                                "ResZone",
                                "IndZone",
                                "SerZone",
                                "PowerPlant",
                                "PowerLine",
                                "Police",
                                "FireStation",
                                "Stadium",
                                "School",
                                "University",
                            ]

                            if building_name in power_conductors:
                                EventBus.publish("recalculate_satisfaction")

                            # Initial image update for zones
                            if hasattr(ent, "update_image"):
                                ent.update_image()
                                if building_name == "ResZone":
                                    EventBus.publish(
                                        "notify", "RESIDENT AREA BUILT", (100, 200, 255)
                                    )
                                    EventBus.publish("recalculate_satisfaction")
                                elif building_name in ["IndZone", "SerZone"]:
                                    EventBus.publish("notify", "NEW WORKPLACE BUILT", (255, 165, 0))
                                    EventBus.publish("recalculate_satisfaction")

                            if building_name == "Road":
                                EventBus.publish("notify", "ROAD CONNECTED", (200, 200, 200))
                            elif building_name in [
                                "Police",
                                "Stadium",
                                "FireStation",
                                "School",
                                "University",
                                "PowerPlant",
                            ]:
                                EventBus.publish(
                                    "notify", f"NEW {building_name.upper()} BUILT!", (255, 255, 100)
                                )
                                # Recalculate satisfaction immediately to apply new bonuses
                                EventBus.publish("recalculate_satisfaction")

                        # Do not deselect if it's a Road or PowerLine for continuous construction
                        if building_name not in ["Road", "PowerLine", "Tree"]:
                            self.hud.selected_tile = None
                        else:
                            # Re-check affordability for continuous placement
                            if not self.resource_manager.is_affordable(building_name):
                                self.hud.selected_tile = None

                        self.examine_tile = None
                        self.hud.examined_tile = None
                        self.examine_mask_points = None
        else:
            if self.can_place_tile(grid_pos):
                building = self.buildings[grid_pos[0]][grid_pos[1]]
                world_tile = self.world[grid_pos[0]][grid_pos[1]]["tile"]

                # Select building to examine
                if mouse_action[0]:
                    if building is not None:
                        self.examine_tile = building.origin
                        self.hud.examined_tile = building
                        self.examine_mask_points = pg.mask.from_surface(building.image).outline()
                    elif world_tile in ["tree", "rock"]:
                        self.examine_tile = (grid_pos[0], grid_pos[1])
                        feature = Scenery(world_tile, self.tiles[world_tile])
                        self.hud.examined_tile = feature
                        self.examine_mask_points = pg.mask.from_surface(feature.image).outline()
                    else:
                        self.examine_tile = None
                        self.hud.examined_tile = None
                        self.examine_mask_points = None

                # Dynamic update of examined tile for real-time stats (saturation etc)
                if self.examine_tile and self.buildings[self.examine_tile[0]][self.examine_tile[1]]:
                    self.hud.examined_tile = self.buildings[self.examine_tile[0]][
                        self.examine_tile[1]
                    ]

    def draw(self, screen, camera):
        screen.blit(self.grass_tiles, (camera.scroll.x, camera.scroll.y))

        # Pre-calculate global offsets outside the tight loop to save CPU cycles
        offset_x = self.grass_tiles.get_width() / 2 + camera.scroll.x
        offset_y = camera.scroll.y

        render_queue = []

        # --- CAMERA CULLING ---

        tl_x, tl_y = self.mouse_to_grid(0, 0, camera.scroll)
        tr_x, tr_y = self.mouse_to_grid(self.width, 0, camera.scroll)
        bl_x, bl_y = self.mouse_to_grid(0, self.height, camera.scroll)
        br_x, br_y = self.mouse_to_grid(self.width, self.height, camera.scroll)
        min_x = int(min(tl_x, tr_x, bl_x, br_x))
        max_x = int(max(tl_x, tr_x, bl_x, br_x))
        min_y = int(min(tl_y, tr_y, bl_y, br_y))
        max_y = int(max(tl_y, tr_y, bl_y, br_y))
        PADDING = 6
        start_x = max(0, min_x - PADDING)
        end_x = min(self.grid_length_x, max_x + PADDING)
        start_y = max(0, min_y - PADDING)
        end_y = min(self.grid_length_y, max_y + PADDING)

        for x in range(start_x, end_x):
            for y in range(start_y, end_y):
                render_pos = self.world[x][y]["render_pos"]
                screen_x = render_pos[0] + offset_x

                # --- World Tiles (Trees, Rocks) ---
                tile_key = self.world[x][y]["tile"]
                if tile_key != "":
                    tile_img = self.tiles[tile_key]
                    screen_y = render_pos[1] - (tile_img.get_height() - TILE_SIZE) + offset_y

                    # Calculate isometric depth (x + width + y + height)
                    depth = x + 0.5 + y + 0.5

                    mask = None
                    if (
                        self.examine_tile == (x, y)
                        and self.buildings[x][y] is None
                        and self.examine_mask_points
                    ):
                        mask = [
                            (mx + screen_x, my + screen_y) for mx, my in self.examine_mask_points
                        ]

                    render_queue.append(
                        {
                            "image": tile_img,
                            "pos": (screen_x, screen_y),
                            "depth": depth,
                            "mask": mask,
                        }
                    )

                # --- Buildings ---
                building = self.buildings[x][y]
                if building is not None and building.origin == (x, y):
                    b_w = building.grid_width
                    b_h = building.grid_height

                    cart_x = x * TILE_SIZE
                    cart_y = y * TILE_SIZE
                    multi_rect = [
                        (cart_x, cart_y),
                        (cart_x + b_w * TILE_SIZE, cart_y),
                        (cart_x + b_w * TILE_SIZE, cart_y + b_h * TILE_SIZE),
                        (cart_x, cart_y + b_h * TILE_SIZE),
                    ]
                    multi_iso = [self.cart_to_iso(px, py) for px, py in multi_rect]
                    minx = min(px for px, py in multi_iso)
                    miny = min(py for px, py in multi_iso)

                    b_screen_x = minx + offset_x
                    floor_height = (b_w + b_h) * (TILE_SIZE / 2)
                    b_screen_y = miny - (building.image.get_height() - floor_height) + offset_y

                    # Calculate depth specifically for multi-tile buildings
                    depth = x + (b_w / 2.0) + y + (b_h / 2.0)

                    mask = None
                    if self.examine_tile == (x, y) and self.examine_mask_points:
                        mask = [
                            (mx + b_screen_x, my + b_screen_y)
                            for mx, my in self.examine_mask_points
                        ]

                    render_queue.append(
                        {
                            "image": building.image,
                            "pos": (b_screen_x, b_screen_y),
                            "depth": depth,
                            "mask": mask,
                            "on_fire": getattr(building, "on_fire", False),
                        }
                    )

                # --- Workers ---
                worker = self.workers[x][y]
                if worker is not None:
                    w_screen_y = render_pos[1] - (worker.image.get_height() - TILE_SIZE) + offset_y
                    depth = x + 0.5 + y + 0.5
                    render_queue.append(
                        {
                            "image": worker.image,
                            "pos": (render_pos[0] + offset_x, w_screen_y),
                            "depth": depth,
                            "mask": None,
                        }
                    )

        if getattr(self.game, "dinosaur_entity", None) is not None:
            dino = self.game.dinosaur_entity
            d_render_pos = dino.tile["render_pos"]
            d_screen_x = d_render_pos[0] + offset_x
            d_screen_y = d_render_pos[1] - (dino.image.get_height() - TILE_SIZE) + offset_y

            dx, dy = dino.tile["grid"]
            d_depth = dx + 0.5 + dy + 0.5
            render_queue.append(
                {
                    "image": dino.image,
                    "pos": (d_screen_x, d_screen_y),
                    "depth": d_depth,
                    "mask": None,
                }
            )

        for ent in self.entities:
            if getattr(ent, "name", "") in ["FireTruck", "Car"]:
                ft_render_pos = ent.tile["render_pos"]
                ft_screen_x = ft_render_pos[0] + offset_x
                ft_screen_y = ft_render_pos[1] - (ent.image.get_height() - TILE_SIZE) + offset_y

                dx, dy = ent.tile["grid"]
                ft_depth = dx + 0.5 + dy + 0.5
                render_queue.append(
                    {
                        "image": ent.image,
                        "pos": (ft_screen_x, ft_screen_y),
                        "depth": ft_depth,
                        "mask": None,
                    }
                )

        # 2. Sort the queue by our calculated depth!
        render_queue.sort(key=lambda q_item: q_item["depth"])

        # 3. Render everything from back-to-front
        for item in render_queue:
            screen.blit(item["image"], item["pos"])
            if item["mask"]:
                pg.draw.polygon(screen, (255, 255, 255), item["mask"], 3)

            if item.get("on_fire") and self.fire_images:
                curr_fire_img = self.fire_images[self.fire_current_frame]
                fx = (
                    item["pos"][0]
                    + (item["image"].get_width() // 2)
                    - (curr_fire_img.get_width() // 2)
                )
                fy = (
                    item["pos"][1]
                    + (item["image"].get_height() // 2)
                    - (curr_fire_img.get_height() // 2)
                )
                screen.blit(curr_fire_img, (fx, fy))

        # 4. Draw Ghost Tile last so it stays completely visible as a UI overlay
        if self.temp_tile is not None:
            iso_poly = self.temp_tile["iso_poly"]
            shifted_poly = [(px + offset_x, py + offset_y) for px, py in iso_poly]

            color = (255, 0, 0) if self.temp_tile["collision"] else (255, 255, 255)
            pg.draw.polygon(screen, color, shifted_poly, 3)

            render_pos = self.temp_tile["render_pos"]
            img = self.temp_tile["image"]
            b_w = self.temp_tile.get("b_w", 1)
            b_h = self.temp_tile.get("b_h", 1)

            floor_height = (b_w + b_h) * (TILE_SIZE / 2)
            screen_y = render_pos[1] - (img.get_height() - floor_height) + offset_y

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
                    self.tiles["block"], (render_pos[0] + center_offset_x, render_pos[1])
                )

        return world

    def grid_to_world(self, grid_x, grid_y):
        rect = [
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE),
            (grid_x * TILE_SIZE + TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE),
            (grid_x * TILE_SIZE, grid_y * TILE_SIZE + TILE_SIZE),
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
            "collision": tile != "",  # Simplified boolean logic
        }

    def create_collision_matrix(self):
        collision_matrix = [
            [1 for _ in range(self.grid_length_x)] for _ in range(self.grid_length_y)
        ]
        for grid_x in range(self.grid_length_x):
            for grid_y in range(self.grid_length_y):
                if self.world[grid_x][grid_y]["collision"]:
                    collision_matrix[grid_y][grid_x] = 0
        return collision_matrix

    @staticmethod
    def cart_to_iso(x, y):
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
            "tree": pg.image.load(TREE_URL).convert_alpha(),
            "rock": pg.image.load(ROCK_URL).convert_alpha(),
            "block": pg.image.load(BLOCK_URL).convert_alpha(),
        }

    def can_place_tile(self, grid_pos):
        mouse_pos = pg.mouse.get_pos()

        # Check HUD panels using any() for cleaner, short-circuit logic
        hud_rects = [self.hud.resource_rect, self.hud.build_rect, self.hud.select_rect]

        if hasattr(self.hud, "dino_btn_rect"):
            hud_rects.append(self.hud.dino_btn_rect)

        if getattr(self.game, "menu_state", None) == "CONFIRM_DEMOLISH" and hasattr(
            self.hud, "demo_box_rect"
        ):
            hud_rects.append(self.hud.demo_box_rect)

        if any(rect.collidepoint(mouse_pos) for rect in hud_rects):
            return False

        # BUG FIX: changed `self.grid_length_x` to `self.grid_length_y` for the Y axis check
        world_bounds = (0 <= grid_pos[0] < self.grid_length_x) and (
            0 <= grid_pos[1] < self.grid_length_y
        )
        return world_bounds

    def is_area_free(self, origin_x, origin_y, width, height):
        for x in range(origin_x, origin_x + width):
            for y in range(origin_y, origin_y + height):
                if not (0 <= x < self.grid_length_x and 0 <= y < self.grid_length_y):
                    return False
                if self.world[x][y]["collision"]:
                    return False
        return True

    def has_road_access(self, x, y, b_width, b_height):
        """Checks if a building at (x,y) with dimensions (w,h) is adjacent to a road."""
        # Check all tiles around the perimeter
        for i in range(x - 1, x + b_width + 1):
            for j in range(y - 1, y + b_height + 1):
                # Skip the tiles the building itself occupies
                if x <= i < x + b_width and y <= j < y + b_height:
                    continue
                if 0 <= i < self.grid_length_x and 0 <= j < self.grid_length_y:
                    b = self.buildings[i][j]
                    if b and b.name == "Road":
                        return True
        return False

    def get_adjacent_roads(self, x, y, b_width, b_height):
        """Returns a list of (x, y) coordinates of roads adjacent to the building."""
        roads = []
        for i in range(x - 1, x + b_width + 1):
            for j in range(y - 1, y + b_height + 1):
                if x <= i < x + b_width and y <= j < y + b_height:
                    continue
                if 0 <= i < self.grid_length_x and 0 <= j < self.grid_length_y:
                    b = self.buildings[i][j]
                    if b and b.name == "Road":
                        roads.append((i, j))
        return roads

    def is_road_safe_to_demolish(self, x, y):
        """
        Checks if a road at (x, y) can be safely demolished without breaking
        connectivity between existing zones.
        """
        from collections import deque

        all_zones = []
        for bx in range(self.grid_length_x):
            for by in range(self.grid_length_y):
                b = self.buildings[bx][by]
                if isinstance(b, Zone) and b.origin == (bx, by):
                    all_zones.append(b)

        if not all_zones:
            return True  # No zones to disconnect

        # Helper to get road network connectivity
        def get_road_networks(exclude_pos=None):
            networks = {}  # (rx, ry) -> network_id
            visited = set()
            net_id = 0
            # Optimize: only iterate over coordinates that HAVE roads
            road_positions = []
            for rx in range(self.grid_length_x):
                for ry in range(self.grid_length_y):
                    b = self.buildings[rx][ry]
                    if b and b.name == "Road":
                        road_positions.append((rx, ry))

            for rx, ry in road_positions:
                if (rx, ry) == exclude_pos:
                    continue
                if (rx, ry) not in visited:
                    queue = deque([(rx, ry)])
                    visited.add((rx, ry))
                    while queue:
                        cx, cy = queue.popleft()
                        networks[(cx, cy)] = net_id
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = cx + dx, cy + dy
                            if (nx, ny) == exclude_pos:
                                continue
                            if 0 <= nx < self.grid_length_x and 0 <= ny < self.grid_length_y:
                                nb = self.buildings[nx][ny]
                                if nb and nb.name == "Road" and (nx, ny) not in visited:
                                    visited.add((nx, ny))
                                    queue.append((nx, ny))
                    net_id += 1
            return networks

        # Get networks BEFORE removal
        current_networks = get_road_networks()

        # Map zones to their networks BEFORE removal
        def get_zone_networks(zone, networks_map):
            adj = self.get_adjacent_roads(
                zone.origin[0], zone.origin[1], zone.grid_width, zone.grid_height
            )
            return {networks_map[r] for r in adj if r in networks_map}

        zone_to_nets_before = {z: get_zone_networks(z, current_networks) for z in all_zones}

        # Get networks AFTER removal
        future_networks = get_road_networks(exclude_pos=(x, y))
        zone_to_nets_after = {z: get_zone_networks(z, future_networks) for z in all_zones}

        # Check if any previously connected zones are now in different networks or disconnected
        # This is a bit tricky. If two zones shared a network before, they must share one after.
        for i in range(len(all_zones)):
            for j in range(i + 1, len(all_zones)):
                z1 = all_zones[i]
                z2 = all_zones[j]

                nets1_before = zone_to_nets_before[z1]
                nets2_before = zone_to_nets_before[z2]

                # If they were connected via at least one common network
                if nets1_before.intersection(nets2_before):
                    # They MUST still be connected via at least one common network after
                    nets1_after = zone_to_nets_after[z1]
                    nets2_after = zone_to_nets_after[z2]
                    if not nets1_after.intersection(nets2_after):
                        return False

        return True

    def execute_demolition(self, grid_pos, pay_compensation=0, apply_penalty=0, refund=True):
        has_building = self.buildings[grid_pos[0]][grid_pos[1]] is not None
        is_rock = self.world[grid_pos[0]][grid_pos[1]]["tile"] == "rock"

        if has_building:
            b = self.buildings[grid_pos[0]][grid_pos[1]]

            EventBus.publish("play_sound", "destruction")

            # 1. Apply financial and satisfaction consequences
            if pay_compensation > 0:
                self.resource_manager.funds -= pay_compensation
                self.resource_manager.log_transaction(
                    self.game, "EVICTION PAYOUT", 0, pay_compensation
                )
                EventBus.publish(
                    "notify", f"PAID COMPENSATION: -${pay_compensation:,}", (255, 100, 100)
                )

            if apply_penalty > 0:
                self.resource_manager.eviction_penalty += apply_penalty
                EventBus.publish(
                    "notify", f"CITIZENS ANGERED! (-{apply_penalty}% Sat)", (255, 50, 50)
                )

            # 2. Rehousing Logic for ResZones
            if b.name == "ResZone" and getattr(b, "occupants", 0) > 0:
                displaced = b.occupants
                other_res = [
                    z for z in self.entities if getattr(z, "name", "") == "ResZone" and z != b
                ]

                # Try to fit them into other zones
                for z in other_res:
                    if displaced <= 0:
                        break
                    space = z.capacity - z.occupants
                    if space > 0:
                        moved = min(displaced, space)
                        z.occupants += moved
                        displaced -= moved
                        if hasattr(z, "update_image"):
                            z.update_image()

                # Citizens who couldn't find a home leave the city forever
                if displaced > 0:
                    # Distribute evictions proportionally across education levels
                    if self.resource_manager.population > 0:
                        sec_ratio = (
                            self.resource_manager.edu_secondary / self.resource_manager.population
                        )
                        tert_ratio = (
                            self.resource_manager.edu_tertiary / self.resource_manager.population
                        )
                        sec_left = int(displaced * sec_ratio)
                        tert_left = int(displaced * tert_ratio)
                        self.resource_manager.edu_secondary = max(
                            0, self.resource_manager.edu_secondary - sec_left
                        )
                        self.resource_manager.edu_tertiary = max(
                            0, self.resource_manager.edu_tertiary - tert_left
                        )
                    self.resource_manager.population = max(
                        0, self.resource_manager.population - displaced
                    )
                    res = self.resource_manager
                    for _ in range(displaced):
                        if res.edu_primary > 0:
                            res.edu_primary -= 1
                        elif res.edu_secondary > 0:
                            res.edu_secondary -= 1
                        elif res.edu_tertiary > 0:
                            res.edu_tertiary -= 1
                    EventBus.publish(
                        "notify", f"{displaced} CITIZENS LEFT THE CITY!", (255, 50, 50)
                    )
                else:
                    EventBus.publish("notify", "ALL DISPLACED CITIZENS REHOUSED", (100, 255, 100))

            # 3. Process Salvage Refund
            if refund:
                refund_percent = (
                    ZONE_REFUND_PERCENT if hasattr(b, "occupants") else BUILDING_REFUND_PERCENT
                )
                cost = self.resource_manager.costs.get(b.name, 0)
                refund_amount = int(cost * refund_percent)
                self.resource_manager.funds += refund_amount
                if refund_amount > 0:
                    self.resource_manager.log_transaction(
                        self.game, f"SALVAGE {b.name}", refund_amount, 0
                    )

            # 4. Remove Entity and Clear Matrix
            if b in self.entities:
                self.entities.remove(b)

            b_w = b.grid_width
            b_h = b.grid_height
            ox, oy = b.origin

            for x in range(ox, ox + b_w):
                for y in range(oy, oy + b_h):
                    self.buildings[x][y] = None
                    self.world[x][y]["collision"] = False
                    self.collision_matrix[y][x] = 1

            # 5. Handle Connectivity Updates
            if b.name == "Road":
                for e in self.entities:
                    if hasattr(e, "has_road_access"):
                        e.has_road_access = self.has_road_access(
                            e.origin[0], e.origin[1], e.grid_width, e.grid_height
                        )

            # 6. Clear UI targeting
            if self.examine_tile == b.origin:
                self.examine_tile = None
                self.hud.examined_tile = None
                self.examine_mask_points = None

            EventBus.publish("recalculate_satisfaction")

        elif is_rock:
            if self.examine_tile == (grid_pos[0], grid_pos[1]):
                self.examine_tile = None
                self.hud.examined_tile = None
                self.examine_mask_points = None

            self.world[grid_pos[0]][grid_pos[1]]["tile"] = ""
            self.world[grid_pos[0]][grid_pos[1]]["collision"] = False
            self.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
            EventBus.publish("play_sound", "destruction")
            EventBus.publish("notify", "ROCK SMASHED!", (200, 200, 200))

    def process_fires(self):
        now = pg.time.get_ticks()
        stations = [b for b in self.entities if getattr(b, "name", "") == "FireStation"]

        for b in self.entities.copy():
            if not hasattr(b, "on_fire") or b.name in ["Road", "Tree", "FireStation"]:
                continue

            # --- START LOGIC ---
            if not b.on_fire:
                chance = CHANCE * 0.01
                if b.name in ["PowerPlant", "IndZone"]:
                    chance = CHANCE * 0.1  # Higher risk

                # Check station radius
                is_protected = False
                for station in stations:
                    dist = abs(b.origin[0] - station.origin[0]) + abs(
                        b.origin[1] - station.origin[1]
                    )
                    if dist <= FIRE_STATION_RADIUS:
                        is_protected = True
                        break

                if is_protected:
                    chance *= 0.1  # 90% reduction

                import random

                if random.random() < chance:
                    b.on_fire = True
                    b.fire_start_time = now
                    b.targeted_by_truck = False
                    EventBus.publish("notify", "IT'S FUCKING BURNING!!!!", (255, 50, 50))

            # --- SPREAD LOGIC ---
            elif b.on_fire:
                if now - b.fire_start_time > FIRE_SPREAD_TIME:
                    adj = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    # Check every tile the building occupies, not just the top-left!
                    for x in range(b.origin[0], b.origin[0] + b.grid_width):
                        for y in range(b.origin[1], b.origin[1] + b.grid_height):
                            for dx, dy in adj:
                                nx, ny = x + dx, y + dy
                                if 0 <= nx < self.grid_length_x and 0 <= ny < self.grid_length_y:
                                    neighbor = self.buildings[nx][ny]
                                    if (
                                        neighbor
                                        and neighbor != b
                                        and hasattr(neighbor, "on_fire")
                                        and not neighbor.on_fire
                                        and neighbor.name not in ["Road", "Tree", "FireStation"]
                                    ):
                                        neighbor.on_fire = True
                                        neighbor.fire_start_time = now
                                        neighbor.targeted_by_truck = False
                                        EventBus.publish("notify", "FIRE SPREAD!", (255, 100, 50))

                    EventBus.publish("notify", f"{b.name.upper()} BURNED DOWN!", (255, 50, 50))
                    self.execute_demolition(b.origin, apply_penalty=10, refund=False)
                    continue

                # --- DISPATCH TRUCK ---
                if not b.targeted_by_truck and stations:
                    closest_station = min(
                        stations,
                        key=lambda st: (
                            abs(b.origin[0] - st.origin[0]) + abs(b.origin[1] - st.origin[1])
                        ),
                    )
                    from .workers import FireTruck

                    FireTruck(closest_station, b, self)
                    b.targeted_by_truck = True
