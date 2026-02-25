class Tool:
    def __init__(self, name):
        self.name = name

    def can_use(self, grid_pos, world):
        return False

    def use(self, grid_pos, world):
        pass

class Axe(Tool):
    def __init__(self):
        super().__init__("Axe")

    def can_use(self, grid_pos, world):
        return world.world[grid_pos[0]][grid_pos[1]]["tile"] == "tree"

    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            world.world[grid_pos[0]][grid_pos[1]]["tile"] = ""
            world.world[grid_pos[0]][grid_pos[1]]["collision"] = False
            world.collision_matrix[grid_pos[1]][grid_pos[0]] = 1

class Hammer(Tool):
    def __init__(self):
        super().__init__("Hammer")

    def can_use(self, grid_pos, world):
        has_building = world.buildings[grid_pos[0]][grid_pos[1]] is not None
        is_rock = world.world[grid_pos[0]][grid_pos[1]]["tile"] == "rock"
        return has_building or is_rock

    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            has_building = world.buildings[grid_pos[0]][grid_pos[1]] is not None
            is_rock = world.world[grid_pos[0]][grid_pos[1]]["tile"] == "rock"

            if has_building:
                building_to_remove = world.buildings[grid_pos[0]][grid_pos[1]]

                if building_to_remove in world.entities:
                    world.entities.remove(building_to_remove)

                # --- NEW: Clear ALL tiles the building occupied ---
                b_w = building_to_remove.grid_width
                b_h = building_to_remove.grid_height
                ox, oy = building_to_remove.origin

                for x in range(ox, ox + b_w):
                    for y in range(oy, oy + b_h):
                        world.buildings[x][y] = None
                        world.world[x][y]["collision"] = False
                        world.collision_matrix[y][x] = 1

                # Deselect if we destroy the currently examined building
                if world.examine_tile == building_to_remove.origin:
                    world.examine_tile = None
                    world.hud.examined_tile = None
                    world.examine_mask_points = None

            elif is_rock:
                world.world[grid_pos[0]][grid_pos[1]]["tile"] = ""

                # Free up the tile for rocks
                world.world[grid_pos[0]][grid_pos[1]]["collision"] = False
                world.collision_matrix[grid_pos[1]][grid_pos[0]] = 1