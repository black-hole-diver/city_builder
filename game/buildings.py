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

        self.on_fire = False
        self.fire_start_time = 0
        self.targeted_by_truck = False
        
    def update(self, game_speed=1):
        pass

class Tree(Building):
    def __init__(self, pos, image, resource_manager, grid_pos, is_old_tree=False, plant_date=None):
        super().__init__(pos, image, "Tree", resource_manager, grid_pos, grid_width=1, grid_height=1)
        self.is_old_tree = is_old_tree
        self.plant_date = plant_date

    def get_age_days(self, current_date):
        if self.is_old_tree or not self.plant_date:
            return 3650  # Max age (10 years)
        return (current_date - self.plant_date).days

    def get_age_formatted(self, current_date):
        if self.is_old_tree:
            return "Old tree (Mature)"
        days = self.get_age_days(current_date)
        years = days // 365
        months = (days % 365) // 30
        rem_days = (days % 365) % 30
        return f"{years} Years, {months} Months, {rem_days} Days"

    def get_bonus_multiplier(self, current_date):
        if self.is_old_tree:
            return 1.0
        days = self.get_age_days(current_date)
        return min(1.0, days / 3650.0) # Scales from 0.0 to 1.0 over 10 years

class Zone(Building):
    def __init__(self, pos, image, name, resource_manager, grid_pos):
        super().__init__(pos, image, name, resource_manager, grid_pos, grid_width=4, grid_height=4)
        self.capacity = ZONE_CAPACITY
        self.occupants = 0
        self.is_vip = False

        self.local_satisfaction = 100
        self.bonuses = []
        
        # Images for different levels of saturation
        self.base_image = image
        self.lvl1_image = None
        self.lvl2_image = None
        self.lvl3_image = None

    def apply_vip(self):
        if not self.is_vip:
            from .hud import Hud
            self.is_vip = True
            self.capacity *= 2
            self.update_image()
            return True
        return False

    def update_image(self):
        if self.is_vip and self.lvl3_image:
            old_image = self.image
            self.image = self.lvl3_image
            if self.game and old_image != self.image:
                self.game.add_notification(f"{self.name} UPGRADED TO VIP!", (255, 215, 0))
            return
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
        self.lvl3_image = pg.image.load(RESZONE_URL4).convert_alpha()


class IndZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "IndZone", resource_manager, grid_pos)
        from .hud import Hud
        self.lvl1_image = Hud.format_isometric_asset(pg.image.load(INDZONE_URL2).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl2_image = Hud.format_isometric_asset(pg.image.load(INDZONE_URL3).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl3_image = pg.image.load(INDZONE_URL4).convert_alpha()

class SerZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "SerZone", resource_manager, grid_pos)
        from .hud import Hud
        self.lvl1_image = Hud.format_isometric_asset(pg.image.load(SERZONE_URL2).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl2_image = Hud.format_isometric_asset(pg.image.load(SERZONE_URL3).convert_alpha(), is_flat=True, grid_w=4, grid_h=4)
        self.lvl3_image = pg.image.load(SERZONE_URL4).convert_alpha()

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
        self.capacity = 50
        self.occupants = 0

class University(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Universities occupy a 4x4 area
        super().__init__(pos, image, "University", resource_manager, grid_pos, grid_width=4, grid_height=4)
        self.capacity = 200
        self.occupants = 0

class PowerPlant(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Power Plants occupy a 4x4 area
        super().__init__(pos, image, "PowerPlant", resource_manager, grid_pos, grid_width=4, grid_height=4)