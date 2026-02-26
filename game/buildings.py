import pygame as pg
from .setting import *
class Building:
    def __init__(self, pos, image, name, resource_manager, grid_pos, grid_width=1, grid_height=1):
        self.image = image
        self.name = name
        self.rect = self.image.get_rect(topleft=pos)
        self.resource_manager = resource_manager
        # Added reference to game via world
        self.game = None # Will be set by World after creation

        self.origin = grid_pos
        self.grid_width = grid_width
        self.grid_height = grid_height
        self.has_road_access = False
        
    def update(self, game_speed=1):
        pass

class Zone(Building):
    def __init__(self, pos, image, name, resource_manager, grid_pos):
        super().__init__(pos, image, name, resource_manager, grid_pos, grid_width=4, grid_height=4)
        self.capacity = ZONE_CAPACITY
        self.occupants = 0
        self.local_satisfaction = 100
        self.bonuses = []
        
        # Images for different levels of saturation
        self.base_image = image
        self.lvl1_image = None
        self.lvl2_image = None

    def update_image(self):
        saturation = self.occupants / self.capacity if self.capacity > 0 else 0
        old_image = self.image
        
        if self.occupants == 0:
            self.image = self.base_image
        elif saturation <= 0.5:
            self.image = self.lvl1_image if self.lvl1_image else self.base_image
        else:
            self.image = self.lvl2_image if self.lvl2_image else (self.lvl1_image if self.lvl1_image else self.base_image)
            
        # Notification for upgrade
        if self.game and old_image != self.image and self.occupants > 0:
            # Only notify when moving to a higher level (saturation increasing)
            # URL1 -> URL2 or URL2 -> URL3
            if old_image == self.base_image and self.image == self.lvl1_image:
                 self.game.add_notification(f"{self.name} UPGRADED (LVL 1)!", (100, 255, 255))
            elif (old_image == self.lvl1_image or old_image == self.base_image) and self.image == self.lvl2_image:
                 self.game.add_notification(f"{self.name} UPGRADED (LVL 2)!", (255, 255, 100))

    @property
    def saturation(self):
        return (self.occupants / self.capacity) * 100 if self.capacity > 0 else 0

# ZONES

class ResZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "ResZone", resource_manager, grid_pos)
        from .hud import Hud
        self.lvl1_image = Hud.format_isometric_asset(pg.image.load(RESZONE_URL2).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl2_image = Hud.format_isometric_asset(pg.image.load(RESZONE_URL3).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)

class IndZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "IndZone", resource_manager, grid_pos)
        from .hud import Hud
        self.lvl1_image = Hud.format_isometric_asset(pg.image.load(INDZONE_URL2).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl2_image = Hud.format_isometric_asset(pg.image.load(INDZONE_URL3).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)

class SerZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "SerZone", resource_manager, grid_pos)
        from .hud import Hud
        self.lvl1_image = Hud.format_isometric_asset(pg.image.load(SERZONE_URL2).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl2_image = Hud.format_isometric_asset(pg.image.load(SERZONE_URL3).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)

# SECURITY & SERVICE

class Police(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Police", resource_manager, grid_pos, grid_width=2, grid_height=2)

class Stadium(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Stadium", resource_manager, grid_pos, grid_width=4, grid_height=4)

class FireStation(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "FireStation", resource_manager, grid_pos, grid_width=2, grid_height=2)

# CONNECTIONS
class Road(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Road", resource_manager, grid_pos, grid_width=1, grid_height=1)

class PowerLine(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "PowerLine", resource_manager, grid_pos, grid_width=1, grid_height=1)

# ADVANCED ENTITIES

class School(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Schools occupy a 2x2 area
        super().__init__(pos, image, "School", resource_manager, grid_pos, grid_width=2, grid_height=2)

class University(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Universities occupy a 4x4 area
        super().__init__(pos, image, "University", resource_manager, grid_pos, grid_width=4, grid_height=4)

class PowerPlant(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Power Plants occupy a 4x4 area
        super().__init__(pos, image, "PowerPlant", resource_manager, grid_pos, grid_width=4, grid_height=4)