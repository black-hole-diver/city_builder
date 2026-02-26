class ResourceManager:
    def __init__(self):
        self.funds = 20_800
        self.population = 0
        self.satisfaction = 100
        
        # Win/Loss tracking
        self.years_negative_budget = 0
        self.is_mayor_replaced = False

        # costs
        self.costs = {
            "Axe":0,
            "Hammer":0,
            "IndZone": 50,
            "SerZone": 50,
            "ResZone": 50,
            "Stadium": 5000,
            "Police": 500,
            "Road": 10,
            "FireStation": 500,
            "School": 1000,
            "University": 5000,
            "PowerPlant": 10000,
            "PowerLine": 5
        }

        self.maintenance_fees = {
            "Road": 1,
            "Police": 50,
            "Stadium": 200,
            "FireStation": 50,
            "School": 100,
            "University": 500,
            "PowerPlant": 1000,
            "PowerLine": 1,
            "ResZone": 5,
            "IndZone": 5,
            "SerZone": 5
        }

        self.tax_per_citizen = 10
        self.tax_rate_satisfaction_impact = 0 # 0 means normal taxes

        # Loans
        self.loans = [] # List of {amount, interest_rate}
        self.total_loan_amount = 0

    def take_loan(self, amount):
        interest_rate = 0.05 # 5% annual interest
        self.loans.append({"amount": amount, "interest": interest_rate})
        self.funds += amount
        self.total_loan_amount += amount

    def repay_loan(self, amount):
        if self.funds >= amount and self.total_loan_amount >= amount:
            self.funds -= amount
            self.total_loan_amount -= amount
            # Simplify repayment: reduce from total, and eventually clear list if 0
            if self.total_loan_amount == 0:
                self.loans = []
            return True
        return False

    def apply_cost_to_resource(self, building):
        cost = self.costs.get(building, 0)
        self.funds -= cost

    def is_affordable(self, building):
        cost = self.costs.get(building, 0)
        return self.funds >= cost

    def apply_annual_budget(self, world):
        # The amount of tax collected depends on how many people live or work in the given zone field.
        
        # Calculate total occupants across all zones (Residential, Industrial, Service)
        total_occupants = 0
        processed_zones = set()
        for x in range(world.grid_length_x):
            for y in range(world.grid_length_y):
                b = world.buildings[x][y]
                if b and hasattr(b, "occupants") and b not in processed_zones:
                    total_occupants += b.occupants
                    processed_zones.add(b)
        
        # Taxation: annual fixed tax amount levied on each zone space based on how many people live or work there.
        tax_income = total_occupants * self.tax_per_citizen
        
        # Loan interest: 5% of total loan amount
        loan_interest = int(self.total_loan_amount * 0.05)
        
        maintenance_cost = 0
        processed_buildings = set()
        for x in range(world.grid_length_x):
            for y in range(world.grid_length_y):
                b = world.buildings[x][y]
                if b and b not in processed_buildings:
                    maintenance_cost += self.maintenance_fees.get(b.name, 0)
                    processed_buildings.add(b)

        maintenance_cost += loan_interest
        self.funds += tax_income
        self.funds -= maintenance_cost
        
        if self.funds < 0:
            self.years_negative_budget += 1
        else:
            self.years_negative_budget = 0
            
        return tax_income, maintenance_cost