from game.event_bus import EventBus
from .buildings import Tree, Road, ResZone, Zone
from .setting import GameEvent, EntityType, GridKey


class Tool:
    def __init__(self, name):
        self.name = name

    def can_use(self, grid_pos, world):
        return False

    def use(self, grid_pos, world):
        pass


class Axe(Tool):
    def __init__(self):
        super().__init__(EntityType.AXE)

    def can_use(self, grid_pos, world):
        b = world.buildings[grid_pos[0]][grid_pos[1]]
        return b is not None and isinstance(b, Tree)

    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            b = world.buildings[grid_pos[0]][grid_pos[1]]

            if world.examine_tile == b.origin:
                world.examine_tile = None
                world.hud.examined_tile = None
                world.examine_mask_points = None

            world.buildings[grid_pos[0]][grid_pos[1]] = None
            world.world[grid_pos[0]][grid_pos[1]][GridKey.COLLISION] = False
            world.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
            if b in world.entities:
                world.entities.remove(b)

            EventBus.publish(GameEvent.PLAY_SOUND, "wood_chop")
            EventBus.publish(GameEvent.NOTIFY, "TIMBERRR! TREE CUT DOWN", (100, 255, 100))
            EventBus.publish(GameEvent.RECALC_SATISFACTION)


class Hammer(Tool):
    def __init__(self):
        super().__init__(EntityType.HAMMER)

    def can_use(self, grid_pos, world):
        has_building = world.buildings[grid_pos[0]][grid_pos[1]] is not None
        is_rock = world.world[grid_pos[0]][grid_pos[1]][GridKey.TILE] == EntityType.ROCK
        return has_building or is_rock

    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            has_building = world.buildings[grid_pos[0]][grid_pos[1]] is not None
            is_rock = world.world[grid_pos[0]][grid_pos[1]][GridKey.TILE] == EntityType.ROCK

            if has_building:
                b = world.buildings[grid_pos[0]][grid_pos[1]]
                is_occupied_zone = hasattr(b, "occupants") and b.occupants > 0

                # Check if it's a road and if its removal breaks connectivity
                is_critical_road = False
                if isinstance(b, Road):
                    if not world.game.construction_manager.is_road_safe_to_demolish(
                        grid_pos[0], grid_pos[1]
                    ):
                        is_critical_road = True

                # Trigger warning ONLY for occupied zones or critical roads
                if is_occupied_zone or is_critical_road:
                    # Calculate consequences
                    stats = {
                        "type": b.name,
                        "occupants": getattr(b, "occupants", 0),
                        "cost": 0,
                        "sat_penalty": 0,
                        "leavers": 0,
                    }

                    if is_occupied_zone:
                        if isinstance(b, ResZone):
                            # Check available housing in other zones
                            other_res = [
                                z for z in world.entities if isinstance(z, ResZone) and z != b
                            ]
                            available_beds = sum(z.capacity - z.occupants for z in other_res)

                            stats["leavers"] = max(0, b.occupants - available_beds)
                            stats["cost"] = b.occupants * 100  # $100 payout per displaced citizen
                            stats["sat_penalty"] = 15  # 15% satisfaction hit
                        else:
                            stats["cost"] = b.occupants * 50  # $50 severance per fired worker
                            stats["sat_penalty"] = 10
                    elif is_critical_road:
                        stats["cost"] = 250  # Road disruption fee
                        stats["sat_penalty"] = 5

                    # Pause and trigger the UI confirmation
                    world.game.hud.demolish_target_pos = grid_pos
                    world.game.hud.demolish_stats = stats
                    world.game.hud.active_modal = "CONFIRM_DEMOLISH"
                    EventBus.publish(GameEvent.IGNORE_CLICKS)
                else:
                    EventBus.publish(GameEvent.EXECUTE_DEMOLITION, grid_pos)
                    EventBus.publish(GameEvent.IGNORE_CLICKS)
            elif is_rock:
                EventBus.publish(GameEvent.EXECUTE_DEMOLITION, grid_pos)
                EventBus.publish(GameEvent.IGNORE_CLICKS)


class VIP(Tool):
    def __init__(self):
        super().__init__(EntityType.VIP)

    def can_use(self, grid_pos, world):
        b = world.buildings[grid_pos[0]][grid_pos[1]]
        has_funds = world.resource_manager.is_affordable(EntityType.VIP)
        is_valid_zone = b is not None and isinstance(b, Zone)
        return is_valid_zone and not getattr(b, "is_vip", False) and has_funds

    def use(self, grid_pos, world):
        if self.can_use(grid_pos, world):
            b = world.buildings[grid_pos[0]][grid_pos[1]]
            if hasattr(b, "apply_vip") and b.apply_vip():
                world.resource_manager.apply_cost_to_resource(EntityType.VIP, world.game)
                EventBus.publish(GameEvent.PLAY_SOUND, "creation")

                # Deselect examine tile so the HUD updates immediately
                if world.examine_tile == b.origin:
                    world.examine_tile = None
                    world.hud.examined_tile = None
                    world.examine_mask_points = None

                EventBus.publish(GameEvent.RECALC_SATISFACTION)
