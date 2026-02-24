import pygame as pg
from .setting import PRODUCE

class Building:
    def __init__(self, pos, image, name, resource_manager, grid_pos, grid_width=1, grid_height=1):
        # .convert_alpha() speeds up rendering for transparent images
        self.image = image
        self.name = name
        self.rect = self.image.get_rect(topleft=pos)
        self.resource_manager = resource_manager

        # multidimensional params
        self.origin = grid_pos
        self.grid_width = grid_width
        self.grid_height = grid_height

        self.resource_manager.apply_cost_to_resource(self.name)
        self.resource_cooldown = pg.time.get_ticks()

    def update(self, game_speed=1):
        now = pg.time.get_ticks()
        adjusted_cooldown = 2000 / game_speed
        if now - self.resource_cooldown > adjusted_cooldown:
            self.resource_manager.resources[PRODUCE[self.name]] += 1
            self.resource_cooldown = now

class Lumbermill(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Lumbermill", resource_manager, grid_pos)


class Stonemasonry(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Stonemasonry", resource_manager, grid_pos)

class ResZone(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "ResZone", resource_manager, grid_pos, grid_width=4, grid_height=4)
    def update(self, game_speed=1):
        pass

class Stadium(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Stadium", resource_manager, grid_pos, grid_width=6, grid_height=6)
    def update(self, game_speed=1):
        pass