import pygame as pg
import random

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder

from game.event_bus import EventBus
from .setting import (
    FIRETRUCK_URL,
    WORKER_SPEED,
    CAR_URL,
    WORKER_URL,
    DINOSAUR_URL,
)


def is_ready_to_move(entity, now, game_speed):
    """Checks if enough time has passed for the entity to take its next step."""
    return (now - entity.move_timer) > (entity.speed / game_speed)


def load_entity_image(url, fallback_url=WORKER_URL, scale_factor=2, target_w=None):
    """Load entity image based on URL and scale factors"""
    try:
        img = pg.image.load(url).convert_alpha()
    except (FileNotFoundError, pg.error):
        img = pg.image.load(fallback_url).convert_alpha()
    if target_w:
        orig_w, orig_h = img.get_size()
        target_h = int(orig_h * (target_w / orig_w))
        img = pg.transform.smoothscale(img, (target_w, target_h))
    if scale_factor != 1:
        img = pg.transform.scale(
            img, (int(img.get_width() * scale_factor), int(img.get_height() * scale_factor))
        )
    return img


def build_nav_matrix(world, walkable_building_names, unblock_zones):
    """Build matrix from building names and unblocked zones"""
    matrix = [[0 for _ in range(world.grid_length_x)] for _ in range(world.grid_length_y)]

    for x in range(world.grid_length_x):
        for y in range(world.grid_length_y):
            b = world.buildings[x][y]
            if b and b.name in walkable_building_names:
                matrix[y][x] = 1

    for b in unblock_zones:
        for x in range(b.origin[0], b.origin[0] + b.grid_width):
            for y in range(b.origin[1], b.origin[1] + b.grid_height):
                if 0 <= x < world.grid_length_x and 0 <= y < world.grid_length_y:
                    matrix[y][x] = 1

    return matrix


def get_astar_path(matrix, start_grid, end_grid):
    """Get A* path from matrix and destination"""
    grid = Grid(matrix=matrix)
    start_node = grid.node(start_grid[0], start_grid[1])
    end_node = grid.node(end_grid[0], end_grid[1])

    finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
    path, _ = finder.find_path(start_node, end_node, grid)

    return [(node.x, node.y) for node in path] if path else []


class Worker:
    def __init__(self, tile, world):
        self.path = None
        self.path_index = None
        self.end = None
        self.start = None
        self.grid = None
        self.world = world
        self.world.entities.append(self)
        self.name = "worker"
        self.tile = tile
        self.speed = WORKER_SPEED

        self.world.workers[tile["grid"][0]][tile["grid"][1]] = self
        self.image = load_entity_image(WORKER_URL)
        self.move_timer = pg.time.get_ticks()

        self.create_path()

    def create_path(self):
        searching_for_path = True
        attempts = 0
        while searching_for_path and attempts < 100:
            attempts += 1
            x = random.randint(0, self.world.grid_length_x - 1)
            y = random.randint(0, self.world.grid_length_y - 1)
            if not self.world.world[x][y]["collision"]:
                self.path = get_astar_path(self.world.collision_matrix, self.tile["grid"], (x, y))
                if self.path:
                    self.path_index = 0
                    searching_for_path = False

        if searching_for_path:
            self.path = None
            self.move_timer = pg.time.get_ticks() + 2000  # wait 2 seconds before retrying

    def change_tile(self, new_tile):
        self.world.workers[self.tile["grid"][0]][self.tile["grid"][1]] = None
        self.world.workers[new_tile[0]][new_tile[1]] = self
        self.tile = self.world.world[new_tile[0]][new_tile[1]]

    def update(self, game_speed=1):
        now = pg.time.get_ticks()
        if not self.path:
            if now > self.move_timer:
                self.create_path()
            return
        if is_ready_to_move(self, now, game_speed):
            if self.path_index >= len(self.path):
                self.create_path()
                return
            self.change_tile(self.path[self.path_index])
            self.path_index += 1
            self.move_timer = now


class Dinosaur(Worker):
    def __init__(self, tile, world):
        self.path = None
        self.path_index = None
        self.end = None
        self.start = None
        self.grid = None
        self.world = world
        self.world.entities.append(self)
        self.image = load_entity_image(DINOSAUR_URL)
        self.speed = 300
        self.name = "dinosaur"
        self.tile = tile

        self.move_timer = pg.time.get_ticks()
        self.create_path()

    def change_tile(self, new_tile):
        """Dinosaur changes its tile
        DO NOT register the dinosaur in self.world.workers grid
        to prevent blocking normal citizens."""
        self.tile = self.world.world[new_tile[0]][new_tile[1]]


class FireTruck:
    def __init__(self, station, target_building, world):
        self.name = "FireTruck"
        self.world = world
        self.speed = 300
        self.station = station
        self.target = target_building
        self.state = "TO_FIRE"  # States: TO_FIRE, EXTINGUISHING, TO_STATION
        self.extinguish_timer = 0
        self.fire_extinguish_time = 2000
        self.image = load_entity_image(FIRETRUCK_URL, target_w=64)

        self.tile = self.world.world[station.origin[0]][station.origin[1]]
        self.path = []
        self.path_index = 0
        self.move_timer = pg.time.get_ticks()

        self.world.entities.append(self)
        self.create_path(self.target.origin)

    def create_path(self, dest_origin):
        """Create a temporary copy of the collision matrix."""
        matrix_copy = build_nav_matrix(self.world, ["Road", ""], [self.station, self.target])

        for y in range(self.world.grid_length_y):
            for x in range(self.world.grid_length_x):
                if self.world.collision_matrix[y][x] == 1 and matrix_copy[y][x] == 0:
                    matrix_copy[y][x] = self.world.collision_matrix[y][x]

        self.path = get_astar_path(matrix_copy, self.tile["grid"], dest_origin)
        self.path_index = 0

    def update(self, game_speed=1):
        now = pg.time.get_ticks()

        if self.target not in self.world.entities and self.state != "TO_STATION":
            self.state = "TO_STATION"
            self.create_path(self.station.origin)
            self.target = self.station
            return

        if self.state == "EXTINGUISHING":
            if now - self.extinguish_timer > self.fire_extinguish_time / game_speed:
                self.target.on_fire = False
                self.target.targeted_by_truck = False
                self.target.fire_start_time = 0
                EventBus.publish("notify", "FIRE EXTINGUISHED!", (100, 200, 255))
                self.state = "TO_STATION"
                self.create_path(self.station.origin)
            return

        if not self.path or self.path_index >= len(self.path):
            if self.state == "TO_FIRE":
                dist_x = abs(self.tile["grid"][0] - self.target.origin[0])
                dist_y = abs(self.tile["grid"][1] - self.target.origin[1])
                if dist_x <= 5 and dist_y <= 5:
                    self.state = "EXTINGUISHING"
                    self.extinguish_timer = now
                else:
                    self.target.targeted_by_truck = False
                    if self in self.world.entities:
                        self.world.entities.remove(self)
            elif self.state == "TO_STATION":
                if self in self.world.entities:
                    self.world.entities.remove(self)
            return

        if is_ready_to_move(self, now, game_speed):
            new_pos = self.path[self.path_index]
            self.tile = self.world.world[new_pos[0]][new_pos[1]]
            self.path_index += 1
            self.move_timer = now


class Car:
    def __init__(self, start_zone, target_zone, world):
        self.name = "Car"
        self.world = world
        self.start = start_zone
        self.target = target_zone
        self.speed = 40
        self.image = load_entity_image(CAR_URL)

        self.tile = self.world.world[start_zone.origin[0]][start_zone.origin[1]]
        self.path = []
        self.path_index = 0
        self.move_timer = pg.time.get_ticks()
        self.stuck_timer = 0  # Prevents deadlock traffic jams

        self.create_path(self.target.origin)

        # Only add to the world IFF a road path is found
        if self.path:
            self.world.entities.append(self)
        else:
            if hasattr(self.target, "targeted_by_truck"):
                self.target.targeted_by_truck = False

    def create_path(self, dest_origin):
        # Create a strict matrix: ONLY Roads are walkable (1)
        matrix_copy = build_nav_matrix(self.world, ["Road"], [self.start, self.target])
        self.path = get_astar_path(matrix_copy, self.tile["grid"], dest_origin)
        self.path_index = 0

    def update(self, game_speed=1):
        now = pg.time.get_ticks()

        if not self.path or self.path_index >= len(self.path):
            if self in self.world.entities:
                self.world.entities.remove(self)
            return

        if is_ready_to_move(self, now, game_speed):
            new_pos = self.path[self.path_index]

            # Check if the tile we are about to drive onto is still valid
            next_building = self.world.buildings[new_pos[0]][new_pos[1]]

            is_valid_terrain = next_building and (
                next_building.name == "Road"
                or next_building == self.start
                or next_building == self.target
            )

            if not is_valid_terrain:
                # IF road destroyed THEN remove car
                if self in self.world.entities:
                    self.world.entities.remove(self)
                return

            occupied = False
            for e in self.world.entities:
                if getattr(e, "name", "") == "Car" and e != self:
                    if e.tile["grid"][0] == new_pos[0] and e.tile["grid"][1] == new_pos[1]:
                        occupied = True
                        break

            if occupied:
                self.stuck_timer += now - self.move_timer
                # IF stuck for 3 seconds, THEN remove car
                if self.stuck_timer > self.speed / game_speed:
                    if self in self.world.entities:
                        self.world.entities.remove(self)
            else:
                self.tile = self.world.world[new_pos[0]][new_pos[1]]
                self.path_index += 1
                self.stuck_timer = 0

            self.move_timer = now
