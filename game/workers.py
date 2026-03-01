import pygame as pg
import random

from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from .setting import WORKER_SPEED, CAR_URL, WORKER_URL


class Worker:
    def __init__(self, tile, world):
        self.path = None
        self.path_index = None
        self.end = None
        self.start = None
        self.grid = None
        self.world = world
        self.world.entities.append(self)
        image = pg.image.load("assets/graphics/worker.png").convert_alpha()
        self.name = "worker"
        self.image = pg.transform.scale(image, (image.get_width() * 2, image.get_height() * 2))
        self.tile = tile

        # pathfinding
        self.world.workers[tile["grid"][0]][tile["grid"][1]] = self
        self.move_timer = pg.time.get_ticks()

        self.create_path()

    def create_path(self):
        searching_for_path = True
        attempts = 0
        while searching_for_path and attempts < 100:
            attempts += 1
            x = random.randint(0, self.world.grid_length_x - 1)
            y = random.randint(0, self.world.grid_length_y - 1)
            dest_tile = self.world.world[x][y]
            if not dest_tile["collision"]:
                self.grid = Grid(matrix=self.world.collision_matrix)
                self.start = self.grid.node(self.tile["grid"][0], self.tile["grid"][1])
                self.end = self.grid.node(x, y)
                finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
                self.path_index = 0
                path, runs = finder.find_path(self.start, self.end, self.grid)
                if path:
                    self.path = [(node.x, node.y) for node in path]
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
        adjusted_delay = WORKER_SPEED / game_speed
        if now - self.move_timer > adjusted_delay:
            if self.path_index >= len(self.path):
                self.create_path()
                return
            new_pos = self.path[self.path_index]
            # update position in the world
            self.change_tile(new_pos)
            self.path_index += 1
            self.move_timer = now


class Dinosaur(Worker):
    def __init__(self, tile, world):
        super().__init__(tile, world)
        self.path = None
        self.path_index = None
        self.end = None
        self.start = None
        self.grid = None
        self.world = world
        self.world.entities.append(self)

        try:
            self.image = pg.image.load("assets/graphics/Dinosaur.png").convert_alpha()
        except (FileNotFoundError, pg.error):
            self.image = pg.image.load("assets/graphics/worker.png").convert_alpha()

        self.name = "dinosaur"
        self.tile = tile

        self.move_timer = pg.time.get_ticks()
        self.create_path()

    def change_tile(self, new_tile):
        # We don't register the dinosaur in the self.world.workers grid
        # so it doesn't accidentally block normal citizens.
        self.tile = self.world.world[new_tile[0]][new_tile[1]]

    def update(self, game_speed=1):
        now = pg.time.get_ticks()
        if not self.path:
            if now > self.move_timer:
                self.create_path()
            return

        adjusted_delay = 25 / game_speed
        if now - self.move_timer > adjusted_delay:
            if self.path_index >= len(self.path):
                self.create_path()
            else:
                new_pos = self.path[self.path_index]
                self.change_tile(new_pos)
                self.path_index += 1
                self.move_timer = now


class FireTruck:
    def __init__(self, station, target_building, world):
        self.name = "FireTruck"
        self.world = world
        self.station = station
        self.target = target_building
        self.state = "TO_FIRE"  # States: TO_FIRE, EXTINGUISHING, TO_STATION
        self.extinguish_timer = 0

        try:
            self.image = pg.image.load("assets/graphics/FireTruck.png").convert_alpha()
        except (FileNotFoundError, pg.error):
            self.image = pg.image.load("assets/graphics/worker.png").convert_alpha()

        self.image = pg.transform.scale(
            self.image, (self.image.get_width() * 2, self.image.get_height() * 2)
        )

        self.tile = self.world.world[station.origin[0]][station.origin[1]]
        self.path = []
        self.path_index = 0
        self.move_timer = pg.time.get_ticks()

        self.world.entities.append(self)
        self.create_path(self.target.origin)

    def create_path(self, dest_origin):
        # Create a temporary copy of the collision matrix
        matrix_copy = [row[:] for row in self.world.collision_matrix]

        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                b = self.world.buildings[x][y]
                if b and b.name == "Road":
                    matrix_copy[y][x] = 1

        # Unblock the Station and the Target so the truck can enter them
        for b in [self.station, self.target]:
            for x in range(b.origin[0], b.origin[0] + b.grid_width):
                for y in range(b.origin[1], b.origin[1] + b.grid_height):
                    if 0 <= x < self.world.grid_length_x and 0 <= y < self.world.grid_length_y:
                        matrix_copy[y][x] = 1  # 1 is Walkable

        grid = Grid(matrix=matrix_copy)
        start = grid.node(self.tile["grid"][0], self.tile["grid"][1])
        end = grid.node(dest_origin[0], dest_origin[1])

        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        raw_path, _ = finder.find_path(start, end, grid)
        if raw_path:
            self.path = [(node.x, node.y) for node in raw_path]
        else:
            self.path = []
        self.path_index = 0

    def update(self, game_speed=1):
        now = pg.time.get_ticks()

        if self.target not in self.world.entities and self.state != "TO_STATION":
            self.state = "TO_STATION"
            self.create_path(self.station.origin)
            self.target = self.station
            return

        if self.state == "EXTINGUISHING":
            # Takes 2 seconds to put out the fire
            if now - self.extinguish_timer > 2000 / game_speed:
                self.target.on_fire = False
                self.target.targeted_by_truck = False
                self.target.fire_start_time = 0
                self.world.game.add_notification("FIRE EXTINGUISHED!", (100, 200, 255))
                self.state = "TO_STATION"
                self.create_path(self.station.origin)
            return

        # Movement Logic
        if not self.path or self.path_index >= len(self.path):
            if self.state == "TO_FIRE":
                self.state = "EXTINGUISHING"
                self.extinguish_timer = now
            elif self.state == "TO_STATION":
                # Despawn when arriving back at station
                if self in self.world.entities:
                    self.world.entities.remove(self)
            return

        # Truck moves faster than workers (15ms delay vs 25ms)
        adjusted_delay = 300 / game_speed
        if now - self.move_timer > adjusted_delay:
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

        try:
            self.image = pg.image.load(CAR_URL).convert_alpha()
        except (FileNotFoundError, pg.error):
            self.image = pg.image.load(WORKER_URL).convert_alpha()

        self.image = pg.transform.scale(
            self.image, (self.image.get_width() * 2, self.image.get_height() * 2)
        )

        self.tile = self.world.world[start_zone.origin[0]][start_zone.origin[1]]
        self.path = []
        self.path_index = 0
        self.move_timer = pg.time.get_ticks()
        self.stuck_timer = 0  # Prevents permanent traffic jams

        self.create_path(self.target.origin)

        # Only add to the world if a valid road path was actually found
        if self.path:
            self.world.entities.append(self)

    def create_path(self, dest_origin):
        # Create a strict matrix: ONLY Roads are walkable (1)
        matrix_copy = [
            [0 for _ in range(self.world.grid_length_x)] for _ in range(self.world.grid_length_y)
        ]

        for x in range(self.world.grid_length_x):
            for y in range(self.world.grid_length_y):
                b = self.world.buildings[x][y]
                if b and b.name == "Road":
                    matrix_copy[y][x] = 1

        # Unblock the start and target zones so the car can enter/exit them
        for b in [self.start, self.target]:
            for x in range(b.origin[0], b.origin[0] + b.grid_width):
                for y in range(b.origin[1], b.origin[1] + b.grid_height):
                    if 0 <= x < self.world.grid_length_x and 0 <= y < self.world.grid_length_y:
                        matrix_copy[y][x] = 1

        grid = Grid(matrix=matrix_copy)
        start = grid.node(self.tile["grid"][0], self.tile["grid"][1])
        end = grid.node(dest_origin[0], dest_origin[1])

        finder = AStarFinder(diagonal_movement=DiagonalMovement.never)
        raw_path, _ = finder.find_path(start, end, grid)

        if raw_path:
            self.path = [(node.x, node.y) for node in raw_path]
        else:
            self.path = []
        self.path_index = 0

    def update(self, game_speed=1):
        now = pg.time.get_ticks()

        # Despawn when arriving at the target or if path is done
        if not self.path or self.path_index >= len(self.path):
            if self in self.world.entities:
                self.world.entities.remove(self)
            return

        adjusted_delay = 40 / game_speed  # Car movement speed
        if now - self.move_timer > adjusted_delay:
            new_pos = self.path[self.path_index]

            # --- NEW: ROAD DESTRUCTION CHECK ---
            # Check if the tile we are about to drive onto is still valid
            next_building = self.world.buildings[new_pos[0]][new_pos[1]]

            # It's valid if it's a Road, or if it's our start/target zones
            is_valid_terrain = next_building and (
                next_building.name == "Road"
                or next_building == self.start
                or next_building == self.target
            )

            if not is_valid_terrain:
                # The road was destroyed! Despawn the car to prevent ghost driving.
                if self in self.world.entities:
                    self.world.entities.remove(self)
                return
            # -----------------------------------

            # --- STRICT COLLISION CHECK ---
            occupied = False
            for e in self.world.entities:
                if getattr(e, "name", "") == "Car" and e != self:
                    if e.tile["grid"][0] == new_pos[0] and e.tile["grid"][1] == new_pos[1]:
                        occupied = True
                        break

            if occupied:
                self.stuck_timer += now - self.move_timer
                # If stuck for 3 seconds (head-to-head deadlock), despawn to clear traffic
                if self.stuck_timer > 3000 / game_speed:
                    if self in self.world.entities:
                        self.world.entities.remove(self)
            else:
                self.tile = self.world.world[new_pos[0]][new_pos[1]]
                self.path_index += 1
                self.stuck_timer = 0

            self.move_timer = now
