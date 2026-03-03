from .setting import COSTS, MAINTENANCE_FEES
class ResourceManager:
    def __init__(self):
        self.funds = 20_800
        self._population = 0
        self.satisfaction = 100

        self.edu_secondary = 0
        self.edu_tertiary = 0

        self.years_negative_budget = 0
        self.is_mayor_replaced = False

        self.costs = COSTS
        self.maintenance_fees = MAINTENANCE_FEES

        self.tax_per_citizen = 10
        self.tax_rate_satisfaction_impact = 0  # 0 means normal taxes
        self.eviction_penalty = 0

        self.loans = []  # List of {amount, interest_rate}
        self.total_loan_amount = 0

        self.budget_history = []  # List of {year, income, expenses, balance}

    @property
    def population(self):
        return self._population

    @population.setter
    def population(self, value):
        self._population = max(0, int(value))
        if self.edu_tertiary > self.population:
            self.edu_tertiary = self.population
        if self.edu_secondary + self.edu_tertiary > self._population:
            self.edu_secondary = self._population - self.edu_tertiary

    @property
    def edu_primary(self):
        return max(0, self._population - self.edu_secondary - self.edu_tertiary)

    @edu_primary.setter
    def edu_primary(self, value):
        pass

    def take_loan(self, amount, game=None):
        interest_rate = 0.05  # 5% annual interest
        self.loans.append({"amount": amount, "interest": interest_rate})
        self.funds += amount
        self.total_loan_amount += amount
        if game:
            self.log_transaction(game, "LOAN", amount, 0)

    def repay_loan(self, amount, game=None):
        if self.funds >= amount and self.total_loan_amount >= amount:
            self.funds -= amount
            self.total_loan_amount -= amount
            # Repayment: reduce from total, and eventually clear list if 0
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
        self.budget_history.insert(
            0,
            {
                "time": timestamp,
                "year": game.current_date.year,
                "category": category,
                "income": int(income),
                "expenses": int(expense),
                "balance": int(income - expense),
            },
        )
        # Keep only last 50 transactions to avoid bloat
        if len(self.budget_history) > 50:
            self.budget_history.pop()

    def apply_daily_budget(self, world):
        # Calculate daily tax based on education levels
        # University = 2.0x value, School = 1.5x value, Primary = 1.0x value
        effective_pop = (
            (self.edu_primary * 1.0) + (self.edu_secondary * 1.5) + (self.edu_tertiary * 2.0)
        )

        daily_tax_per_citizen = self.tax_per_citizen / 365.0
        tax_income = effective_pop * daily_tax_per_citizen

        ind_ser_zones = [
            e for e in world.entities if getattr(e, "name", "") in ["IndZone", "SerZone"]
        ]
        total_workers = sum(getattr(z, "occupants", 0) for z in ind_ser_zones)
        unpowered_workers = sum(
            getattr(z, "occupants", 0) for z in ind_ser_zones if not getattr(z, "is_powered", False)
        )

        if total_workers > 0:
            penalty_ratio = unpowered_workers / total_workers
            # Reduce total daily tax proportionally (up to 50% loss if all workplaces lose power)
            tax_income *= 1.0 - (penalty_ratio * 0.5)

        maintenance_cost = (self.total_loan_amount * 0.05) / 365.0

        # Calculate total occupants across all zones (Residential, Industrial, Service)
        processed_buildings = set()
        for x in range(world.grid_length_x):
            for y in range(world.grid_length_y):
                b = world.buildings[x][y]
                if b and b not in processed_buildings:
                    if b.name == "Tree":
                        if not getattr(b, "is_old_tree", False) and getattr(b, "plant_date", None):
                            if (world.game.current_date - b.plant_date).days < 3650:
                                maintenance_cost += 20 / 365.0
                    else:
                        maintenance_cost += self.maintenance_fees.get(b.name, 0) / 365.0
                    processed_buildings.add(b)

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

        if self.eviction_penalty > 0:
            self.eviction_penalty = max(0.0, self.eviction_penalty - 0.5)

        return tax_income, maintenance_cost
