class Building:
    def __init__(self, pos, image, name, resource_manager, grid_pos, grid_width=1, grid_height=1):
        self.image = image
        self.name = name
        self.rect = self.image.get_rect(topleft=pos)
        self.resource_manager = resource_manager

        self.origin = grid_pos
        self.grid_width = grid_width
        self.grid_height = grid_height

        self.resource_manager.apply_cost_to_resource(self.name)
        #self.resource_cooldown = pg.time.get_ticks()

    def update(self, game_speed=1):
        pass

class Zone(Building):
    def __init__(self, pos, image, name, resource_manager, grid_pos):
        super().__init__(pos, image, name, resource_manager, grid_pos, grid_width=4, grid_height=4)
        self.capacity = 10
        self.occupants = 0
        self.has_road_access = False
        self.local_satisfaction = 100

# ZONES

class ResZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "ResZone", resource_manager, grid_pos)

class IndZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "IndZone", resource_manager, grid_pos)

class SerZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "SerZone", resource_manager, grid_pos)

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
        # Schools occupy a 1x2 area
        super().__init__(pos, image, "School", resource_manager, grid_pos, grid_width=2, grid_height=2)

class University(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Universities occupy a 2x2 area
        super().__init__(pos, image, "University", resource_manager, grid_pos, grid_width=4, grid_height=4)

class PowerPlant(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        # Power Plants occupy a 2x2 area
        super().__init__(pos, image, "PowerPlant", resource_manager, grid_pos, grid_width=2, grid_height=2)