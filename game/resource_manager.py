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

        self.budget_history = [] # List of {year, income, expenses, balance}

    def take_loan(self, amount, game=None):
        interest_rate = 0.05 # 5% annual interest
        self.loans.append({"amount": amount, "interest": interest_rate})
        self.funds += amount
        self.total_loan_amount += amount
        if game:
            self.log_transaction(game, "LOAN", amount, 0)

    def repay_loan(self, amount, game=None):
        if self.funds >= amount and self.total_loan_amount >= amount:
            self.funds -= amount
            self.total_loan_amount -= amount
            # Simplify repayment: reduce from total, and eventually clear list if 0
            if self.total_loan_amount == 0:
                self.loans = []
            if game:
                self.log_transaction(game, "REPAY", 0, amount)
            return True
        return False

    def apply_cost_to_resource(self, building, game=None):
        cost = self.costs.get(building, 0)
        self.funds -= cost
        if game:
            self.log_transaction(game, f"BUILD {building}", 0, cost)

    def is_affordable(self, building):
        cost = self.costs.get(building, 0)
        return self.funds >= cost

    def log_transaction(self, game, category, income, expense):
        """Logs a transaction with a game-time timestamp."""
        timestamp = game.current_date.strftime("%Y-%m-%d %H:%M")
        self.budget_history.insert(0, {
            "time": timestamp,
            "year": game.current_date.year,
            "category": category,
            "income": int(income),
            "expenses": int(expense),
            "balance": int(income - expense)
        })
        # Keep only last 50 transactions to avoid bloat
        if len(self.budget_history) > 50:
            self.budget_history.pop()

    def apply_daily_budget(self, world):
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
        
        # Taxation: annual tax / 365 = daily tax
        daily_tax_per_citizen = self.tax_per_citizen / 365.0
        tax_income = total_occupants * daily_tax_per_citizen
        
        # Loan interest: 5% annual interest / 365 = daily interest
        daily_loan_interest = (self.total_loan_amount * 0.05) / 365.0
        
        maintenance_cost = 0
        processed_buildings = set()
        for x in range(world.grid_length_x):
            for y in range(world.grid_length_y):
                b = world.buildings[x][y]
                if b and b not in processed_buildings:
                    # Maintenance fee / 365 = daily maintenance
                    maintenance_cost += self.maintenance_fees.get(b.name, 0) / 365.0
                    processed_buildings.add(b)

        maintenance_cost += daily_loan_interest
        self.funds += tax_income
        self.funds -= maintenance_cost
        
        # Log daily budget if it's significant (> 0.1) or once a month to avoid spam
        if (tax_income > 0.1 or maintenance_cost > 0.1) and world.game.current_date.day == 1:
            self.log_transaction(world.game, "DAILY BUDGET", tax_income, maintenance_cost)

        if self.funds < 0:
            # We only count full years of negative budget for the game over condition
            # This is handled in apply_annual_logic now
            pass
        else:
            self.years_negative_budget = 0
            
        return tax_income, maintenance_cost