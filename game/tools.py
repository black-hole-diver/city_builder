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
                b = world.buildings[grid_pos[0]][grid_pos[1]]

                is_occupied_zone = hasattr(b, "occupants") and b.occupants > 0
                is_road = b.name == "Road"

                # Trigger warning for occupied zones or active roads
                if is_occupied_zone or is_road:
                    # Calculate consequences
                    stats = {
                        "type": b.name,
                        "occupants": getattr(b, "occupants", 0),
                        "cost": 0,
                        "sat_penalty": 0,
                        "leavers": 0
                    }

                    if is_occupied_zone:
                        if b.name == "ResZone":
                            # Check available housing in other zones
                            other_res = [z for z in world.entities if getattr(z, "name", "") == "ResZone" and z != b]
                            available_beds = sum(z.capacity - z.occupants for z in other_res)

                            stats["leavers"] = max(0, b.occupants - available_beds)
                            stats["cost"] = b.occupants * 100  # $100 payout per displaced citizen
                            stats["sat_penalty"] = 15  # 15% satisfaction hit
                        else:
                            stats["cost"] = b.occupants * 50  # $50 severance per fired worker
                            stats["sat_penalty"] = 10
                    elif is_road:
                        stats["cost"] = 250  # Road disruption fee
                        stats["sat_penalty"] = 5

                    # Pause and trigger the UI confirmation
                    world.game.demolish_target_pos = grid_pos
                    world.game.demolish_stats = stats
                    world.game.menu_state = "CONFIRM_DEMOLISH"
                else:
                    # Empty buildings skip the warning and are destroyed instantly
                    world.execute_demolition(grid_pos)
            elif is_rock:
                # Scenery is destroyed instantly
                world.execute_demolition(grid_pos)

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