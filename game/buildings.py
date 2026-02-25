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

class ResZone(Zone):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "ResZone", resource_manager, grid_pos)

class Police(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Police", resource_manager, grid_pos, grid_width=2, grid_height=2)

class Stadium(Building):
    def __init__(self, pos, image, resource_manager, grid_pos):
        super().__init__(pos, image, "Stadium", resource_manager, grid_pos, grid_width=6, grid_height=6)