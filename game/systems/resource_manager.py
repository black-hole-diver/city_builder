from game.setting import COSTS, MAINTENANCE_FEES


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

        # v1.1.0
        self.demographics = {age: 0 for age in range(18, 101)}
        self.historical_tax_rates = []
        self.total_deaths = 0

    def sync_demographics(self):
        """Ensures the statistical demographic tally matches actual zone population."""
        current_sim_pop = sum(self.demographics.values())
        diff = int(self.population) - current_sim_pop
        from random import randint, choice

        if diff > 0:
            for _ in range(diff):
                age = randint(18, 60)
                self.demographics[age] += 1
        elif diff < 0:
            # Pensioners refuse to leave!
            removals_needed = abs(diff)
            working_ages = list(range(18, 65))
            while removals_needed > 0:
                valid_ages = [age for age in working_ages if self.demographics[age] > 0]
                if not valid_ages:
                    break
                target_age = choice(valid_ages)
                self.demographics[target_age] -= 1
                removals_needed -= 1

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
        tax_income = 0
        maintenance_cost = (self.total_loan_amount * 0.05) / 365.0

        processed_buildings = set()
        for x in range(world.grid_length_x):
            for y in range(world.grid_length_y):
                b = world.buildings[x][y]
                if b and b not in processed_buildings:
                    from ..buildings import Tree

                    if isinstance(b, Tree):
                        if not getattr(b, "is_old_tree", False) and getattr(b, "plant_date", None):
                            if (world.game.current_date - b.plant_date).days < 3650:
                                maintenance_cost += 20 / 365.0
                    else:
                        maintenance_cost += self.maintenance_fees.get(b.name, 0) / 365.0
                    processed_buildings.add(b)

        self.funds -= maintenance_cost

        if maintenance_cost > 0.1 and world.game.current_date.day == 1:
            self.log_transaction(world.game, "DAILY EXPENSE", 0, maintenance_cost)

        if self.funds < 0:
            pass
        else:
            self.years_negative_budget = 0

        if self.eviction_penalty > 0:
            self.eviction_penalty = max(0.0, self.eviction_penalty - 0.5)

        return tax_income, maintenance_cost
