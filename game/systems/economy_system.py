from game.event_bus import EventBus
from game.setting import GameEvent


class EconomySystem:
    def __init__(self, world, resource_manager, game_context):
        self.world = world
        self.resource_manager = resource_manager
        self.game = game_context
        EventBus.subscribe(GameEvent.INCREASE_TAX, self.increase_tax)
        EventBus.subscribe(GameEvent.DECREASE_TAX, self.decrease_tax)
        EventBus.subscribe(GameEvent.TAKE_LOAN, self.take_loan)
        EventBus.subscribe(GameEvent.REPAY_LOAN, self.repay_loan)

    def increase_tax(self):
        self.resource_manager.tax_per_citizen += 1
        EventBus.publish(
            GameEvent.NOTIFY,
            f"TAX INCREASED: ${self.resource_manager.tax_per_citizen}",
            (255, 255, 100),
        )
        EventBus.publish(GameEvent.RECALC_SATISFACTION)

    def decrease_tax(self):
        if self.resource_manager.tax_per_citizen > 0:
            self.resource_manager.tax_per_citizen -= 1
            EventBus.publish(
                GameEvent.NOTIFY,
                f"TAX DECREASED: ${self.resource_manager.tax_per_citizen}",
                (100, 255, 255),
            )
            EventBus.publish(GameEvent.RECALC_SATISFACTION)

    def take_loan(self, amount=1000):
        self.resource_manager.take_loan(amount, self.game)
        EventBus.publish(GameEvent.NOTIFY, f"LOAN TAKEN: +${amount:,}", (100, 255, 100))
        EventBus.publish(GameEvent.RECALC_SAT_AND_GROWTH)

    def repay_loan(self, amount=1000):
        if self.resource_manager.repay_loan(amount, self.game):
            EventBus.publish(GameEvent.NOTIFY, f"LOAN REPAID: -${amount:,}", (255, 215, 0))
            EventBus.publish(GameEvent.RECALC_SAT_AND_GROWTH)
        else:
            EventBus.publish(GameEvent.NOTIFY, "NOT ENOUGH FUNDS OR NO LOAN", (255, 100, 100))

    def apply_annual_logic(self):
        """Handle annual events: budget summary, satisfaction, and game over conditions."""
        self._process_demographics_and_pensions()
        current_year = self.game.current_date.year - 1
        year_entry = next(
            (
                item
                for item in self.resource_manager.budget_history
                if item.get("year") == current_year
            ),
            None,
        )
        if year_entry:
            self._notify_annual_budget(year_entry)
        self._check_retirement_and_graduation()
        EventBus.publish(GameEvent.RECALC_SATISFACTION)
        self._check_negative_consecutive_years()
        self._check_game_over_conditions()

    def _process_demographics_and_pensions(self):
        res = self.resource_manager

        if not hasattr(res, "demographics"):
            res.demographics = {age: 0 for age in range(18, 101)}
        if not hasattr(res, "historical_tax_rates"):
            res.historical_tax_rates = []

        res.historical_tax_rates.append(res.tax_per_citizen)
        if len(res.historical_tax_rates) > 20:
            res.historical_tax_rates.pop(0)

        avg_historical_tax = sum(res.historical_tax_rates) / len(res.historical_tax_rates)
        pension_rate = int(avg_historical_tax / 2)

        new_demographics = {age: 0 for age in range(18, 101)}
        total_deaths = 0
        new_retirees = res.demographics.get(64, 0)

        for age in range(18, 100):
            count = res.demographics.get(age, 0)
            if count == 0:
                continue

            if age < 64:
                # Move to next age bracket
                new_demographics[age + 1] = count
            else:
                # Statistical Death Calculation for 65+
                death_chance = ((age - 64) ** 2) / 10000.0
                expected_deaths = int(count * death_chance)
                remainder_chance = (count * death_chance) - expected_deaths

                import random

                if random.random() < remainder_chance:
                    expected_deaths += 1

                deaths = min(count, expected_deaths)
                survivors = count - deaths

                total_deaths += deaths
                new_demographics[age + 1] = survivors

        new_demographics[18] += total_deaths
        res.demographics = new_demographics
        res.total_deaths += total_deaths

        working_pop = sum(res.demographics[age] for age in range(18, 65))
        pension_pop = sum(res.demographics[age] for age in range(65, 101))

        edu_multiplier = 1.0
        if res.population > 0:
            effective_pop = (
                (res.edu_primary * 1.0) + (res.edu_secondary * 1.5) + (res.edu_tertiary * 2.0)
            )
            edu_multiplier = effective_pop / res.population
        total_tax_collected = int((working_pop * res.tax_per_citizen) * edu_multiplier)

        from game.buildings import IndZone, SerZone

        ind_ser_zones = [e for e in self.game.entities if isinstance(e, (IndZone, SerZone))]
        total_workers = sum(getattr(z, "occupants", 0) for z in ind_ser_zones)
        unpowered_workers = sum(
            getattr(z, "occupants", 0) for z in ind_ser_zones if not getattr(z, "is_powered", False)
        )

        if total_workers > 0:
            penalty_ratio = unpowered_workers / total_workers
            total_tax_collected = int(total_tax_collected * (1.0 - (penalty_ratio * 0.5)))

        total_pension_paid = pension_pop * pension_rate

        res.funds += total_tax_collected
        res.funds -= total_pension_paid

        if total_tax_collected > 0:
            res.log_transaction(self.game, "INCOME TAX", total_tax_collected, 0)
        if total_pension_paid > 0:
            res.log_transaction(self.game, "PENSIONS", 0, total_pension_paid)
            EventBus.publish(
                GameEvent.NOTIFY, f"PENSIONS PAID: -${total_pension_paid:,}", (255, 100, 100)
            )

        if total_deaths > 0:
            EventBus.publish(
                GameEvent.NOTIFY, f"{total_deaths} PENSIONERS PASSED AWAY", (150, 150, 150)
            )

        if new_retirees > 0:
            EventBus.publish(GameEvent.NOTIFY, f"{new_retirees} CITIZENS RETIRED!", (255, 200, 100))

        if total_deaths > 0:
            EventBus.publish(
                GameEvent.NOTIFY, f"{total_deaths} ELDERLY CITIZENS PASSED AWAY", (150, 150, 150)
            )
            EventBus.publish(
                GameEvent.NOTIFY, f"{total_deaths} YOUNG ADULTS JOINED THE CITY!", (100, 255, 100)
            )

    def _check_negative_consecutive_years(self):
        if self.resource_manager.funds < 0:
            self.resource_manager.years_negative_budget += 1
        else:
            self.resource_manager.years_negative_budget = 0

    def _check_game_over_conditions(self):
        if self.resource_manager.satisfaction < 10:
            self.resource_manager.is_mayor_replaced = True
            EventBus.publish(GameEvent.NOTIFY, "YOU ARE FIRED!!!!", (255, 0, 0))

        if self.resource_manager.years_negative_budget > 5:
            self.resource_manager.is_mayor_replaced = True
            EventBus.publish(GameEvent.NOTIFY, "GAME OVER: DEBT LIMIT EXCEEDED", (255, 0, 0))

    def _notify_annual_budget(self, year_entry):
        tax = int(year_entry["income"])
        maintenance = int(year_entry["expenses"])
        EventBus.publish(GameEvent.NOTIFY, "TAXING TIME!", (255, 215, 0))
        EventBus.publish(
            GameEvent.NOTIFY,
            f"Annual Budget: +${tax} -${maintenance}",
            (100, 255, 100) if tax >= maintenance else (255, 100, 100),
        )

    def _check_retirement_and_graduation(self):
        from game.buildings import School, University

        attrition_rate = 0.10
        retired_sec = int(self.resource_manager.edu_secondary * attrition_rate)
        retired_tert = int(self.resource_manager.edu_tertiary * attrition_rate)
        self.resource_manager.edu_secondary -= retired_sec
        self.resource_manager.edu_primary += retired_sec
        self.resource_manager.edu_tertiary -= retired_tert
        self.resource_manager.edu_secondary += retired_tert

        # Graduation
        sec_cap = int(self.resource_manager.population * 0.50)
        tert_cap = int(self.resource_manager.population * 0.25)

        schools = [
            e
            for e in self.game.entities
            if isinstance(e, School) and e.has_road_access and getattr(e, "is_powered", False)
        ]
        unis = [
            e
            for e in self.game.entities
            if isinstance(e, University) and e.has_road_access and getattr(e, "is_powered", False)
        ]

        # Schools graduate Primary -> Secondary
        for s in schools:
            # Each school can handle a specific number of students per year
            potential = min(20, getattr(s, "occupants", 0))
            graduates = min(
                potential,
                self.resource_manager.edu_primary,
                max(0, sec_cap - self.resource_manager.edu_secondary),
            )
            self.resource_manager.edu_primary -= graduates
            self.resource_manager.edu_secondary += graduates

        # Universities graduate Secondary -> Tertiary
        for u in unis:
            potential = min(10, getattr(u, "occupants", 0))
            graduates = min(
                potential,
                self.resource_manager.edu_secondary,
                max(0, tert_cap - self.resource_manager.edu_tertiary),
            )
            self.resource_manager.edu_secondary -= graduates
            self.resource_manager.edu_tertiary += graduates

        if len(schools) > 0 or len(unis) > 0:
            EventBus.publish(GameEvent.NOTIFY, "ACADEMIC YEAR COMPLETE", (100, 200, 255))
