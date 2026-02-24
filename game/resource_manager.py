from .setting import INITIAL_WOOD, INITIAL_STONE

class ResourceManager:
    def __init__(self):
        # resources
        self.resources = {
            "wood": INITIAL_WOOD,
            "stone": INITIAL_STONE
        }

        # costs
        self.costs = {
            "Lumbermill": {"wood": 7, "stone": 3},
            "Stonemasonry": {"wood": 3, "stone": 5},
            "Axe":{},
            "Hammer":{},
            "ResZone": {"wood":10, "stone":10},
            "Stadium": {"wood":10, "stone":10}
        }

    def apply_cost_to_resource(self, building):
        for resource,cost in self.costs[building].items():
            self.resources[resource] -= cost

    def is_affordable(self, building):
        affordable = True
        for resource,cost in self.costs[building].items():
            if cost > self.resources[resource]:
                affordable = False
        return affordable