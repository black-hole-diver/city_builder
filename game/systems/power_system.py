from game.setting import POWER_PLANT_SUPPLY, GameEvent
from game.event_bus import EventBus

class PowerSystem:
    def __init__(self, world):
        self.world = world
        EventBus.subscribe(GameEvent.UPDATE_POWER_CONNECTIVITY, self.update_connectivity)

    def update_connectivity(self):
        from game.buildings import (
            PowerPlant,
            PowerLine,
            Zone,
            Police,
            Stadium,
            FireStation,
            School,
            University,
        )

        power_cable = [
            e
            for e in self.world.entities
            if isinstance(
                e, (PowerPlant, PowerLine, Zone, Police, Stadium, FireStation, School, University)
            )
        ]
        for e in power_cable:
            e.is_powered = False
        power_networks = PowerSystem.get_power_networks(power_cable)
        for network in power_networks:
            power_plants = [
                b
                for b in network
                if isinstance(b, PowerPlant) and getattr(b, "has_road_access", False)
            ]
            total_supply = len(power_plants) * POWER_PLANT_SUPPLY
            demand_list = []
            for b in network:
                if isinstance(b, (PowerLine, PowerPlant)):
                    b.is_powered = total_supply > 0
                    continue
                demand = 0
                if isinstance(b, Zone):
                    demand = 5 + getattr(b, "occupants", 0) * 2
                else:
                    demand = 50
                    if isinstance(b, Stadium):
                        demand = 200
                    elif isinstance(b, University):
                        demand = 100
                if demand > 0:
                    demand_list.append((b, demand))
            total_network_demand = sum(dem for _, dem in demand_list)
            all_power_plants_in_network = [b for b in network if isinstance(b, PowerPlant)]
            for pp in all_power_plants_in_network:
                if getattr(pp, "has_road_access", False):
                    pp.network_supply = total_supply
                    pp.network_demand = total_network_demand
                    pp.is_powered = True
                else:
                    pp.network_supply = 0
                    pp.network_demand = 0
                    pp.is_powered = False
            demand_list.sort(
                key=lambda x: 0 if isinstance(x[0], Zone) else 1,
                reverse=True,
            )
            current_supply = total_supply
            for b, dem in demand_list:
                if current_supply >= dem:
                    current_supply -= dem
                    b.is_powered = True
                else:
                    b.is_powered = False

    @staticmethod
    def get_power_networks(power_capable):
        """BFS algorithm to group adjacent buildings into contiguous power grids."""
        from collections import deque

        visited_power = set()
        power_networks = []

        for b in power_capable:
            if b not in visited_power:
                network = []
                queue = deque([b])
                visited_power.add(b)

                while queue:
                    curr = queue.popleft()
                    network.append(curr)

                    for other in power_capable:
                        if other not in visited_power:
                            x_overlap = (
                                curr.origin[0] < other.origin[0] + other.grid_width
                                and curr.origin[0] + curr.grid_width > other.origin[0]
                            )
                            y_overlap = (
                                curr.origin[1] < other.origin[1] + other.grid_height
                                and curr.origin[1] + curr.grid_height > other.origin[1]
                            )

                            x_adj = (
                                curr.origin[0] == other.origin[0] + other.grid_width
                                or curr.origin[0] + curr.grid_width == other.origin[0]
                            ) and y_overlap
                            y_adj = (
                                curr.origin[1] == other.origin[1] + other.grid_height
                                or curr.origin[1] + curr.grid_height == other.origin[1]
                            ) and x_overlap

                            if x_adj or y_adj:
                                visited_power.add(other)
                                queue.append(other)

                power_networks.append(network)

        return power_networks
