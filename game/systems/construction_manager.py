import pygame as pg
from game.event_bus import EventBus
from game.setting import (
    BUILDING_REFUND_PERCENT,
    ZONE_REFUND_PERCENT,
    EntityType,
    GameEvent,
    MusicEvent,
    GridKey,
)
from game.buildings import (
    ResZone,
    Road,
    IndZone,
    SerZone,
    Zone,
    PowerPlant,
    PowerLine,
    Police,
    FireStation,
    Stadium,
    School,
    University,
    Tree,
)
from game.tools import Axe, Hammer, VIP


class ConstructionManager:
    def __init__(self, game, world):
        self.game = game
        self.world = world

        EventBus.subscribe(GameEvent.EXECUTE_DEMOLITION, self.execute_demolition)

        self.building_types = {
            EntityType.RES_ZONE: ResZone,
            EntityType.IND_ZONE: IndZone,
            EntityType.SER_ZONE: SerZone,
            EntityType.STADIUM: Stadium,
            EntityType.POLICE: Police,
            EntityType.FIRE_STATION: FireStation,
            EntityType.SCHOOL: School,
            EntityType.UNIVERSITY: University,
            EntityType.POWER_PLANT: PowerPlant,
            EntityType.ROAD: Road,
            EntityType.POWERLINE: PowerLine,
            EntityType.TREE: Tree,
        }

        self.tools = {EntityType.AXE: Axe(), EntityType.HAMMER: Hammer(), EntityType.VIP: VIP()}

    def can_place_tile(self, grid_pos):
        mouse_pos = pg.mouse.get_pos()
        hud = self.game.hud

        hud_rects = [hud.resource_rect, hud.build_rect, hud.select_rect]
        if hasattr(hud, "dino_btn_rect"):
            hud_rects.append(hud.dino_btn_rect)
        if getattr(self.game, "menu_state", None) == "CONFIRM_DEMOLISH" and hasattr(
            hud, "demo_box_rect"
        ):
            hud_rects.append(hud.demo_box_rect)

        if any(rect.collidepoint(mouse_pos) for rect in hud_rects):
            return False

        world_bounds = (0 <= grid_pos[0] < self.world.grid_length_x) and (
            0 <= grid_pos[1] < self.world.grid_length_y
        )
        return world_bounds

    def is_area_free(self, origin_x, origin_y, width, height):
        for x in range(origin_x, origin_x + width):
            for y in range(origin_y, origin_y + height):
                if not (0 <= x < self.world.grid_length_x and 0 <= y < self.world.grid_length_y):
                    return False
                if self.world.world[x][y][GridKey.COLLISION]:
                    return False
        return True

    def has_road_access(self, x, y, b_width, b_height):
        for i in range(x - 1, x + b_width + 1):
            for j in range(y - 1, y + b_height + 1):
                if x <= i < x + b_width and y <= j < y + b_height:
                    continue
                if 0 <= i < self.world.grid_length_x and 0 <= j < self.world.grid_length_y:
                    b = self.world.buildings[i][j]
                    if isinstance(b, Road):
                        return True
        return False

    def get_adjacent_roads(self, x, y, b_width, b_height):
        roads = []
        for i in range(x - 1, x + b_width + 1):
            for j in range(y - 1, y + b_height + 1):
                if x <= i < x + b_width and y <= j < y + b_height:
                    continue
                if 0 <= i < self.world.grid_length_x and 0 <= j < self.world.grid_length_y:
                    b = self.world.buildings[i][j]
                    if isinstance(b, Road):
                        roads.append((i, j))
        return roads

    def place_building(self, grid_pos, selected_tile, minx, miny):
        building_name = selected_tile["name"]
        building_class = self.building_types.get(building_name)

        if building_class:
            building_image = selected_tile["image"]
            b_width = selected_tile.get("grid_width", 1)
            b_height = selected_tile.get("grid_height", 1)

            kwargs = {}
            if building_name == EntityType.TREE:
                kwargs["plant_date"] = self.game.current_date

            ent = building_class(
                (minx, miny),
                building_image,
                self.game.resource_manager,
                grid_pos,
                **kwargs,
            )
            ent.game = self.game
            self.game.resource_manager.apply_cost_to_resource(building_name, self.game)
            EventBus.publish(GameEvent.PLAY_SOUND, MusicEvent.CREATION_SOUND)

            ent.has_road_access = self.has_road_access(grid_pos[0], grid_pos[1], b_width, b_height)

            self.game.entities.append(ent)
            for x in range(grid_pos[0], grid_pos[0] + b_width):
                for y in range(grid_pos[1], grid_pos[1] + b_height):
                    self.world.buildings[x][y] = ent
                    self.world.world[x][y][GridKey.COLLISION] = True
                    self.world.collision_matrix[y][x] = 0

            # Connectivity Updates
            if isinstance(ent, Road):
                newly_connected = False
                for e in self.game.entities:
                    if hasattr(e, "has_road_access"):
                        was_connected = e.has_road_access
                        e.has_road_access = self.has_road_access(
                            e.origin[0], e.origin[1], e.grid_width, e.grid_height
                        )
                        if not was_connected and e.has_road_access and not isinstance(e, Road):
                            newly_connected = True
                EventBus.publish(GameEvent.RECALC_SATISFACTION)

            if isinstance(
                ent, (Zone, PowerPlant, PowerLine, Police, FireStation, Stadium, School, University)
            ):
                EventBus.publish(GameEvent.RECALC_SATISFACTION)

            if hasattr(ent, "update_image"):
                ent.update_image()
                if isinstance(ent, ResZone):
                    EventBus.publish(GameEvent.NOTIFY, "RESIDENT AREA BUILT", (100, 200, 255))
                elif isinstance(ent, (IndZone, SerZone)):
                    EventBus.publish(GameEvent.NOTIFY, "NEW WORKPLACE BUILT", (255, 165, 0))

            if isinstance(ent, Road) and newly_connected:
                EventBus.publish(GameEvent.NOTIFY, "ROAD CONNECTED", (200, 200, 200))
            elif isinstance(ent, (Police, Stadium, FireStation, School, University, PowerPlant)):
                EventBus.publish(
                    GameEvent.NOTIFY, f"NEW {building_name.upper()} BUILT!", (255, 255, 100)
                )

            return ent
        return None

    def execute_demolition(self, grid_pos, pay_compensation=0, apply_penalty=0, refund=True):
        has_building = self.world.buildings[grid_pos[0]][grid_pos[1]] is not None
        is_rock = self.world.world[grid_pos[0]][grid_pos[1]][GridKey.TILE] == EntityType.ROCK

        if has_building:
            b = self.world.buildings[grid_pos[0]][grid_pos[1]]

            EventBus.publish(GameEvent.PLAY_SOUND, MusicEvent.DESTRUCTION_SOUND)

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
                        e.has_road_access = self.has_road_access(
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
            EventBus.publish(GameEvent.PLAY_SOUND, MusicEvent.DESTRUCTION_SOUND)
            EventBus.publish(GameEvent.NOTIFY, "ROCK SMASHED!", (200, 200, 200))

    def is_road_safe_to_demolish(self, x, y):
        """Check whether destroy the road tile will disconnect the city."""
        from collections import deque
        from game.buildings import Zone, Road

        all_zones = []
        for bx in range(self.world.grid_length_x):
            for by in range(self.world.grid_length_y):
                b = self.world.buildings[bx][by]
                if isinstance(b, Zone) and b.origin == (bx, by):
                    all_zones.append(b)

        if not all_zones:
            return True

        def get_road_networks(exclude_pos=None):
            networks = {}
            visited = set()
            net_id = 0
            road_positions = []
            for rx in range(self.world.grid_length_x):
                for ry in range(self.world.grid_length_y):
                    b = self.world.buildings[rx][ry]
                    if isinstance(b, Road):
                        road_positions.append((rx, ry))

            for rx, ry in road_positions:
                if (rx, ry) == exclude_pos:
                    continue
                if (rx, ry) not in visited:
                    queue = deque([(rx, ry)])
                    visited.add((rx, ry))
                    while queue:
                        cx, cy = queue.popleft()
                        networks[(cx, cy)] = net_id
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            nx, ny = cx + dx, cy + dy
                            if (nx, ny) == exclude_pos:
                                continue
                            if (
                                0 <= nx < self.world.grid_length_x
                                and 0 <= ny < self.world.grid_length_y
                            ):
                                nb = self.world.buildings[nx][ny]
                                if isinstance(nb, Road) and (nx, ny) not in visited:
                                    visited.add((nx, ny))
                                    queue.append((nx, ny))
                    net_id += 1
            return networks

        current_networks = get_road_networks()

        def get_zone_networks(zone, networks_map):
            adj = self.get_adjacent_roads(
                zone.origin[0], zone.origin[1], zone.grid_width, zone.grid_height
            )
            return {networks_map[r] for r in adj if r in networks_map}

        zone_to_nets_before = {z: get_zone_networks(z, current_networks) for z in all_zones}
        future_networks = get_road_networks(exclude_pos=(x, y))
        zone_to_nets_after = {z: get_zone_networks(z, future_networks) for z in all_zones}

        for i in range(len(all_zones)):
            for j in range(i + 1, len(all_zones)):
                z1 = all_zones[i]
                z2 = all_zones[j]
                nets1_before = zone_to_nets_before[z1]
                nets2_before = zone_to_nets_before[z2]
                if nets1_before.intersection(nets2_before):
                    nets1_after = zone_to_nets_after[z1]
                    nets2_after = zone_to_nets_after[z2]
                    if not nets1_after.intersection(nets2_after):
                        return False

        return True
