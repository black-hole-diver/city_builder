from .buildings import Zone, SerZone, IndZone, ResZone
from .setting import *

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
        b = world.buildings[grid_pos[0]][grid_pos[1]]
        return b is not None and b.name == "Tree"

    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            b = world.buildings[grid_pos[0]][grid_pos[1]]

            if world.examine_tile == b.origin:
                world.examine_tile = None
                world.hud.examined_tile = None
                world.examine_mask_points = None

            world.buildings[grid_pos[0]][grid_pos[1]] = None
            world.world[grid_pos[0]][grid_pos[1]]["collision"] = False
            world.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
            if b in world.entities:
                world.entities.remove(b)

            world.game.play_sound("wood_chop")
            world.game.add_notification("TIMBERRR! TREE CUT DOWN", (100, 255, 100))
            world.game.calculate_satisfaction_and_growth()
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

                # --- NEW: Road connectivity check ---
                if building_to_remove.name == "Road":
                    if not world.is_road_safe_to_demolish(grid_pos[0], grid_pos[1]):
                        world.game.add_notification("CANNOT DEMOLISH: BREAKS CONNECTIVITY!", (255, 100, 100))
                        return

                world.game.play_sound("destruction")
                
                # Pop-up for demolition
                if hasattr(building_to_remove, "occupants") and building_to_remove.occupants > 0:
                    world.game.add_notification("FUCK THE PEOPLE, DEMOLISH THE ZONE!!", (255, 50, 50))
                else:
                    world.game.add_notification(f"DEMOLISHED {building_to_remove.name.upper()}", (255, 200, 100))
                
                # Refund logic
                refund_percent = BUILDING_REFUND_PERCENT
                if hasattr(building_to_remove, "occupants"):
                    # Zone refund logic: 50% refund (as per requirement)
                    refund_percent = ZONE_REFUND_PERCENT
                    
                    if building_to_remove.occupants > 0:
                        # Population logic: handle disappeared or displaced citizens
                        if building_to_remove.name == "ResZone":
                            # People in residential zones disappear from the city
                            lost_pop = building_to_remove.occupants
                            world.resource_manager.population -= lost_pop
                            
                            # Also if a residential zone is destroyed then the local population of working zones also effected to that amount
                            # We need to remove 'lost_pop' workers from IndZone and SerZone
                            all_working_zones = []
                            for x in range(world.grid_length_x):
                                for y in range(world.grid_length_y):
                                    b = world.buildings[x][y]
                                    if b and b.name in ["IndZone", "SerZone"] and b.origin == (x, y):
                                        all_working_zones.append(b)
                            
                            # Remove workers one by one from random working zones that have occupants
                            for _ in range(lost_pop):
                                eligible_zones = [z for z in all_working_zones if z.occupants > 0]
                                if eligible_zones:
                                    import random
                                    target_z = random.choice(eligible_zones)
                                    target_z.occupants -= 1
                                    target_z.update_image()
                                else:
                                    break

                        # For IndZone/SerZone, they are workers and will be redistributed in next game update
                        # since population doesn't change, but they lose their current workplace.
                
                cost = world.resource_manager.costs.get(building_to_remove.name, 0)
                refund_amount = int(cost * refund_percent)
                world.resource_manager.funds += refund_amount
                world.resource_manager.log_transaction(world.game, f"REFUND {building_to_remove.name}", refund_amount, 0)

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

                if building_to_remove.name == "ResZone":
                    lost_pop = building_to_remove.occupants
                    res = world.resource_manager
                    # Remove from primary first (simulating youth/low-skilled displacement)
                    for _ in range(lost_pop):
                        if res.edu_primary > 0:
                            res.edu_primary -= 1
                        elif res.edu_secondary > 0:
                            res.edu_secondary -= 1
                        elif res.edu_tertiary > 0:
                            res.edu_tertiary -= 1
                    res.population = max(0, res.population - lost_pop)

                # NEW: Update road access for ALL buildings if we just demolished a road
                if building_to_remove.name == "Road":
                    for e in world.entities:
                        if hasattr(e, "has_road_access"):
                            e.has_road_access = world.has_road_access(e.origin[0], e.origin[1], e.grid_width, e.grid_height)

                # Deselect if we destroy the currently examined building
                if world.examine_tile == building_to_remove.origin:
                    world.examine_tile = None
                    world.hud.examined_tile = None
                    world.examine_mask_points = None
                world.game.calculate_satisfaction_and_growth()

            elif is_rock:
                # Deselect if we destroy the currently examined rock
                if world.examine_tile == (grid_pos[0], grid_pos[1]):
                    world.examine_tile = None
                    world.hud.examined_tile = None
                    world.examine_mask_points = None

                world.world[grid_pos[0]][grid_pos[1]]["tile"] = ""

                # Free up the tile for rocks
                world.world[grid_pos[0]][grid_pos[1]]["collision"] = False
                world.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
                world.game.play_sound("destruction")
                world.game.add_notification("ROCK SMASHED!", (200, 200, 200))

class VIP(Tool):
    def __init__(self):
        super().__init__("VIP")
    def can_use(self, grid_pos, world):
        b = world.buildings[grid_pos[0]][grid_pos[1]]
        has_funds = world.resource_manager.is_affordable("VIP")
        is_valid_zone = b is not None and b.name in ["ResZone", "IndZone", "SerZone"]
        return is_valid_zone and not getattr(b, "is_vip", False) and has_funds
    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            b = world.buildings[grid_pos[0]][grid_pos[1]]
            if hasattr(b, "apply_vip") and b.apply_vip():
                world.resource_manager.apply_cost_to_resource("VIP", world.game)
                world.game.play_sound("creation")

                # Deselect examine tile so the HUD updates immediately
                if world.examine_tile == b.origin:
                    world.examine_tile = None
                    world.hud.examined_tile = None
                    world.examine_mask_points = None

                world.game.calculate_satisfaction_and_growth()