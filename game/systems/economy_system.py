from game.event_bus import EventBus


class EconomySystem:
    def __init__(self, world, resource_manager, game_context):
        self.world = world
        self.resource_manager = resource_manager
        self.game = game_context

    def apply_annual_logic(self):
        """Moved from Game.apply_annual_logic"""
        """Handle annual events: budget summary, satisfaction, and game over conditions."""
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
        EventBus.publish("recalculate_satisfaction")
        self._check_negative_consecutive_years()
        self._check_game_over_conditions()

    def _check_negative_consecutive_years(self):
        if self.resource_manager.funds < 0:
            self.resource_manager.years_negative_budget += 1
        else:
            self.resource_manager.years_negative_budget = 0

    def _check_game_over_conditions(self):
        if self.resource_manager.satisfaction < 10:
            self.resource_manager.is_mayor_replaced = True
            self.game.add_notification("YOU ARE FIRED!!!!", (255, 0, 0))

        if self.resource_manager.years_negative_budget > 5:
            self.resource_manager.is_mayor_replaced = True
            self.game.add_notification("GAME OVER: DEBT LIMIT EXCEEDED", (255, 0, 0))

    def _notify_annual_budget(self, year_entry):
        tax = int(year_entry["income"])
        maintenance = int(year_entry["expenses"])
        self.game.add_notification("TAXING TIME!", (255, 215, 0))
        self.game.add_notification(
            f"Annual Budget: +${tax} -${maintenance}",
            (100, 255, 100) if tax >= maintenance else (255, 100, 100),
        )

    def _check_retirement_and_graduation(self):
        from game.buildings import (
            School,
            University
        )
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
            self.game.add_notification("ACADEMIC YEAR COMPLETE", (100, 200, 255))
