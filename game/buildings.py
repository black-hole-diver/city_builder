import pygame as pg
from .setting import PRODUCE

class Building:
    def __init__(self, pos, image, name, resource_manager):
        # .convert_alpha() speeds up rendering for transparent images
        self.image = image
        self.name = name
        self.rect = self.image.get_rect(topleft=pos)
        self.resource_manager = resource_manager
        self.resource_manager.apply_cost_to_resource(self.name)
        self.resource_cooldown = pg.time.get_ticks()

    def update(self):
        now = pg.time.get_ticks()
        if now - self.resource_cooldown > 2000:
            self.resource_manager.resources[PRODUCE[self.name]] += 1
            self.resource_cooldown = now

class Lumbermill(Building):
    def __init__(self, pos, image, resource_manager):
        super().__init__(pos, image, "Lumbermill", resource_manager)


class Stonemasonry(Building):
    def __init__(self, pos, image, resource_manager):
        super().__init__(pos, image, "Stonemasonry", resource_manager)