class ResourceManager:
    def __init__(self):
        self.funds = 20_800
        self.population = 0
        self.satisfaction = 100

        # costs
        self.costs = {
            "Axe":0,
            "Hammer":0,
            "IndZone": 50,
            "SerZone": 50,
            "ResZone": 50,
            "Stadium": 5000,
            "Police": 500,
            "Road": 10
        }

        self.maintenance_fees = {
            "Road": 1,
            "Police": 50,
            "Stadium": 200,
        }

        self.tax_per_citizen = 10

    def apply_cost_to_resource(self, building):
        cost = self.costs.get(building, 0)
        self.funds -= cost

    def is_affordable(self, building):
        cost = self.costs.get(building, 0)
        return self.funds >= cost

    def apply_annual_budget(self, world):
        tax_income = self.population * self.tax_per_citizen
        maintenance_cost = 0
        processed_buildings = set()
        for x in range(world.grid_length_x):
            for y in range(world.grid_length_y):
                b = world.buildings[x][y]
                if b and b not in processed_buildings:
                    maintenance_cost += self.maintenance_fees.get(b.name, 0)
                    processed_buildings.add(b)

        self.funds += tax_income
        self.funds -= maintenance_cost
        return tax_income, maintenance_cost