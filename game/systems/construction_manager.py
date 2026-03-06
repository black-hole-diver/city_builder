import pygame as pg
from game.event_bus import EventBus
from game.setting import (
    BUILDING_REFUND_PERCENT,
    ZONE_REFUND_PERCENT,
    EntityType,
    GameEvent,
    GridKey,
)
from game.buildings import ResZone, Road


class ConstructionManager:
    def __init__(self, game, world):
        self.game = game
        self.world = world
        EventBus.subscribe(GameEvent.EXECUTE_DEMOLITION, self.execute_demolition)

    def execute_demolition(self, grid_pos, pay_compensation=0, apply_penalty=0, refund=True):
        has_building = self.world.buildings[grid_pos[0]][grid_pos[1]] is not None
        is_rock = self.world.world[grid_pos[0]][grid_pos[1]][GridKey.TILE] == EntityType.ROCK

        if has_building:
            b = self.world.buildings[grid_pos[0]][grid_pos[1]]

            EventBus.publish(GameEvent.PLAY_SOUND, "destruction")

            # 1. Apply financial and satisfaction consequences
            if pay_compensation > 0:
                self.game.resource_manager.funds -= pay_compensation
                self.game.resource_manager.log_transaction(
                    self.game, "EVICTION PAYOUT", 0, pay_compensation
                )
                EventBus.publish(
                    GameEvent.NOTIFY, f"PAID COMPENSATION: -${pay_compensation:,}", (255, 100, 100)
                )

            if apply_penalty > 0:
                self.game.resource_manager.eviction_penalty += apply_penalty
                EventBus.publish(
                    GameEvent.NOTIFY, f"CITIZENS ANGERED! (-{apply_penalty}% Sat)", (255, 50, 50)
                )

            # 2. Rehousing Logic for ResZones
            if isinstance(b, ResZone) and getattr(b, "occupants", 0) > 0:
                displaced = b.occupants
                other_res = [z for z in self.game.entities if isinstance(z, ResZone) and z != b]

                # Try to fit them into other zones
                for z in other_res:
                    if displaced <= 0:
                        break
                    space = z.capacity - z.occupants
                    if space > 0:
                        moved = min(displaced, space)
                        z.occupants += moved
                        displaced -= moved
                        if hasattr(z, "update_image"):
                            z.update_image()

                # Citizens who couldn't find a home leave the city forever
                if displaced > 0:
                    if self.game.resource_manager.population > 0:
                        sec_ratio = (
                            self.game.resource_manager.edu_secondary
                            / self.game.resource_manager.population
                        )
                        tert_ratio = (
                            self.game.resource_manager.edu_tertiary
                            / self.game.resource_manager.population
                        )
                        sec_left = int(displaced * sec_ratio)
                        tert_left = int(displaced * tert_ratio)
                        self.game.resource_manager.edu_secondary = max(
                            0, self.game.resource_manager.edu_secondary - sec_left
                        )
                        self.game.resource_manager.edu_tertiary = max(
                            0, self.game.resource_manager.edu_tertiary - tert_left
                        )

                    self.game.resource_manager.population = max(
                        0, self.game.resource_manager.population - displaced
                    )
                    res = self.game.resource_manager
                    for _ in range(displaced):
                        if res.edu_primary > 0:
                            res.edu_primary -= 1
                        elif res.edu_secondary > 0:
                            res.edu_secondary -= 1
                        elif res.edu_tertiary > 0:
                            res.edu_tertiary -= 1
                    EventBus.publish(
                        GameEvent.NOTIFY, f"{displaced} CITIZENS LEFT THE CITY!", (255, 50, 50)
                    )
                else:
                    EventBus.publish(
                        GameEvent.NOTIFY, "ALL DISPLACED CITIZENS REHOUSED", (100, 255, 100)
                    )

            # 3. Process Salvage Refund
            if refund:
                refund_percent = (
                    ZONE_REFUND_PERCENT if hasattr(b, "occupants") else BUILDING_REFUND_PERCENT
                )
                cost = self.game.resource_manager.costs.get(b.name, 0)
                refund_amount = int(cost * refund_percent)
                self.game.resource_manager.funds += refund_amount
                if refund_amount > 0:
                    self.game.resource_manager.log_transaction(
                        self.game, f"SALVAGE {b.name}", refund_amount, 0
                    )

            # 4. Remove Entity and Clear Matrix
            if b in self.game.entities:
                self.game.entities.remove(b)

            b_w = b.grid_width
            b_h = b.grid_height
            ox, oy = b.origin

            for x in range(ox, ox + b_w):
                for y in range(oy, oy + b_h):
                    self.world.buildings[x][y] = None
                    self.world.world[x][y][GridKey.COLLISION] = False
                    self.world.collision_matrix[y][x] = 1

            # 5. Handle Connectivity Updates
            if isinstance(b, Road):
                for e in self.game.entities:
                    if hasattr(e, "has_road_access"):
                        e.has_road_access = self.world.has_road_access(
                            e.origin[0], e.origin[1], e.grid_width, e.grid_height
                        )

            # 6. Clear UI targeting
            if self.world.examine_tile == b.origin:
                self.world.examine_tile = None
                self.game.hud.examined_tile = None
                self.world.examine_mask_points = None

            EventBus.publish(GameEvent.RECALC_SATISFACTION)

        elif is_rock:
            if self.world.examine_tile == (grid_pos[0], grid_pos[1]):
                self.world.examine_tile = None
                self.game.hud.examined_tile = None
                self.world.examine_mask_points = None

            self.world.world[grid_pos[0]][grid_pos[1]][GridKey.TILE] = ""
            self.world.world[grid_pos[0]][grid_pos[1]][GridKey.COLLISION] = False
            self.world.collision_matrix[grid_pos[1]][grid_pos[0]] = 1
            EventBus.publish(GameEvent.PLAY_SOUND, "destruction")
            EventBus.publish(GameEvent.NOTIFY, "ROCK SMASHED!", (200, 200, 200))
