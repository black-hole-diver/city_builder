import pygame as pg
import random
from game.event_bus import EventBus
from game.setting import FIRE_SPREAD_TIME, FIRE_STATION_RADIUS, CHANCE, GameEvent
from game.buildings import PowerPlant, IndZone, Road, Tree, FireStation, Building
from game.workers import FireTruck


class DisasterSystem:
    def __init__(self, game, world):
        self.game = game
        self.world = world

    def update(self):
        """Processes fire outbreaks, spreading, and firetruck dispatch."""
        now = pg.time.get_ticks()

        stations = [
            b
            for b in self.game.entities
            if isinstance(b, FireStation) and getattr(b, "is_powered", False)
        ]

        for b in self.game.entities.copy():
            if not hasattr(b, "on_fire") or isinstance(b, (Road, Tree, FireStation)):
                continue

            # --- START LOGIC ---
            if not b.on_fire:
                chance = CHANCE * 0.01
                if isinstance(b, (PowerPlant, IndZone)):
                    chance = CHANCE * 0.1  # Higher risk

                is_protected = False
                for station in stations:
                    dist = abs(b.origin[0] - station.origin[0]) + abs(
                        b.origin[1] - station.origin[1]
                    )
                    if dist <= FIRE_STATION_RADIUS:
                        is_protected = True
                        break

                if is_protected:
                    chance *= 0.1  # 90% reduction

                if random.random() < chance:
                    b.on_fire = True
                    b.fire_start_time = now
                    b.targeted_by_truck = False
                    EventBus.publish(GameEvent.NOTIFY, "IT'S FUCKING BURNING!!!!", (255, 50, 50))

            elif b.on_fire:
                if now - b.fire_start_time > FIRE_SPREAD_TIME:
                    adj = [(0, 1), (0, -1), (1, 0), (-1, 0)]
                    for x in range(b.origin[0], b.origin[0] + b.grid_width):
                        for y in range(b.origin[1], b.origin[1] + b.grid_height):
                            for dx, dy in adj:
                                nx, ny = x + dx, y + dy
                                if (
                                    0 <= nx < self.world.grid_length_x
                                    and 0 <= ny < self.world.grid_length_y
                                ):
                                    neighbor = self.world.buildings[nx][ny]
                                    if (
                                        neighbor
                                        and neighbor != b
                                        and hasattr(neighbor, "on_fire")
                                        and not neighbor.on_fire
                                        and not isinstance(neighbor, (Road, Tree, FireStation))
                                    ):
                                        neighbor.on_fire = True
                                        neighbor.fire_start_time = now
                                        neighbor.targeted_by_truck = False
                                        EventBus.publish(
                                            GameEvent.NOTIFY, "FIRE SPREAD!", (255, 100, 50)
                                        )

                    EventBus.publish(
                        GameEvent.NOTIFY, f"{b.name.upper()} BURNED DOWN!", (255, 50, 50)
                    )
                    EventBus.publish(
                        GameEvent.EXECUTE_DEMOLITION,
                        b.origin,
                        pay_compensation=0,
                        apply_penalty=10,
                        refund=False,
                    )
                    continue

                # --- DISPATCH TRUCK ---
                if not b.targeted_by_truck and stations:
                    closest_station = min(
                        stations,
                        key=lambda st: (
                            abs(b.origin[0] - st.origin[0]) + abs(b.origin[1] - st.origin[1])
                        ),
                    )
                    FireTruck(closest_station, b, self.world)
                    b.targeted_by_truck = True
    def start_random_fire(self):
        """Instantly sets a random building on fire for testing purposes."""
        valid_buildings = [
            b for b in self.game.entities
            if isinstance(b, Building)
            and not isinstance(b, (Road, Tree, FireStation))
            and not getattr(b, "on_fire", False)
        ]
        if valid_buildings:
            target = random.choice(valid_buildings)
            target.on_fire = True
            target.fire_start_time = pg.time.get_ticks()
            target.targeted_by_truck = False
            EventBus.publish(GameEvent.NOTIFY, f"DEBUG: IGNITED {target.name}!", (255, 50, 50))
        else:
            EventBus.publish(GameEvent.NOTIFY, "DEBUG: NO VALID BUILDINGS TO BURN", (200, 200, 200))