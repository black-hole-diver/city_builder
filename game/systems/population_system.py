import random
from game.event_bus import EventBus
from game.buildings import ResZone, IndZone, SerZone, Road
from game.setting import (
    INDUSTRIAL_NEGATIVE_RADIUS,
    POLICE_RADIUS,
    STADIUM_RADIUS,
    GROWTH_SATISFACTION_THRESHOLD,
    DECLINE_SATISFACTION_THRESHOLD,
    BASE_GROWTH_RATE,
    STARTER_CITY_BOOST,
    STARTER_POPULATION_LIMIT,
    GROWTH_SCALER,
    BASE_DECLINE_RATE,
    GameEvent,
)
from game.utils import get_line, logger


class PopulationSystem:
    def __init__(self, world, resource_manager, game_context):
        self.world = world
        self.resource_manager = resource_manager
        self.game = game_context
        EventBus.subscribe(
            GameEvent.RECALC_SATISFACTION,
            lambda: self.calculate_satisfaction_and_growth(skip_growth=True),
        )
        EventBus.subscribe(
            GameEvent.RECALC_SAT_AND_GROWTH,
            lambda: self.calculate_satisfaction_and_growth(skip_growth=False),
        )

    def calculate_satisfaction_and_growth(self, skip_growth=True):
        """Calculate satisfaction levels, population growth, and workplace assignments."""
        res_zones, ind_zones, ser_zones, services, _ = self._zone_distribution()
        self._update_road_access()
        road_networks = self._get_road_networks()
        EventBus.publish(GameEvent.UPDATE_POWER_CONNECTIVITY)
        self._update_fire_protection()

        total_ind_jobs = sum(z.capacity for z in ind_zones if z.has_road_access)
        total_ser_jobs = sum(z.capacity for z in ser_zones if z.has_road_access)
        workforce = sum(rz.occupants for rz in res_zones)
        total_jobs_available = total_ind_jobs + total_ser_jobs
        all_zones = res_zones + ind_zones + ser_zones

        lingering_eviction_penalty = self._calculate_lingering_eviction_penalty()
        loan_penalty = self._calculate_loan_penalty()
        tax_impact = self._calculate_tax_impact()
        imbalance_penalty = self._calculate_industrial_service_imbalance_penalty(
            total_ind_jobs, total_ser_jobs
        )

        total_sat = (
            100 - (imbalance_penalty + loan_penalty + lingering_eviction_penalty) + tax_impact
        )

        # -- Calculate Individual Zone Satisfaction and Bonuses ---
        self._calculate_individual_zone_satisfaction(
            all_zones,
            total_sat,
            road_networks,
            total_jobs_available,
            workforce,
            loan_penalty,
            tax_impact,
            imbalance_penalty,
            services,
            ind_zones,
        )
        self._calculate_overall_city_satisfaction(res_zones)
        if not skip_growth:
            self._calculate_population_growth(res_zones)

        # -- Education and Workplace Assignments ---
        self._workplace_assignment(ind_zones, ser_zones, res_zones)
        self._update_zone_images(ind_zones, ser_zones, res_zones)
        self._education_assignment()

    def _zone_distribution(self):
        """Distributing the zone in to lits"""
        from game.buildings import Police, Stadium

        res_zones = []
        ind_zones = []
        ser_zones = []
        services = []
        roads = []
        for entity in self.game.entities:
            if isinstance(entity, ResZone):
                res_zones.append(entity)
            elif isinstance(entity, IndZone):
                ind_zones.append(entity)
            elif isinstance(entity, SerZone):
                ser_zones.append(entity)
            elif isinstance(entity, Road):
                roads.append(entity)
            elif isinstance(entity, (Police, Stadium)):
                services.append(entity)
        return res_zones, ind_zones, ser_zones, services, roads

    def _update_road_access(self):
        """Update road access for all entities."""
        for e in self.game.entities:
            if hasattr(e, "has_road_access"):
                e.has_road_access = self.world.has_road_access(
                    e.origin[0], e.origin[1], e.grid_width, e.grid_height
                )

    def _get_road_networks(self):
        """Map each road to its network ID using BFS."""
        from collections import deque

        road_networks = {}  # (x, y) -> network_id
        next_network_id = 0
        visited_roads = set()

        for r in [e for e in self.game.entities if isinstance(e, Road)]:
            rx, ry = r.origin
            if (rx, ry) not in visited_roads:
                queue = deque([(rx, ry)])
                visited_roads.add((rx, ry))
                while queue:
                    cx, cy = queue.popleft()
                    road_networks[(cx, cy)] = next_network_id

                    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        nx, ny = cx + dx, cy + dy
                        if (
                            0 <= nx < self.world.grid_length_x
                            and 0 <= ny < self.world.grid_length_y
                        ):
                            nb = self.world.buildings[nx][ny]
                            if isinstance(nb, Road) and (nx, ny) not in visited_roads:
                                visited_roads.add((nx, ny))
                                queue.append((nx, ny))
                next_network_id += 1

        return road_networks

    def _get_touched_networks(self, zone, road_networks):
        """Get all road networks adjacent to this zone."""
        adj_roads = self.world.get_adjacent_roads(
            zone.origin[0], zone.origin[1], zone.grid_width, zone.grid_height
        )
        return {road_networks[r_pos] for r_pos in adj_roads if r_pos in road_networks}

    def _calculate_lingering_eviction_penalty(self):
        """Calculate a lingering satisfaction penalty for recent evictions.
        The penalty decays over time, as the lasting impact of evictions on citizen morale.
        Decay rate is 5 points per day, the penalty reduced by 5 each day until it reaches 0."""
        lingering_eviction_penalty = 0
        if self.resource_manager.eviction_penalty > 0:
            lingering_eviction_penalty += int(self.resource_manager.eviction_penalty)
            self.resource_manager.eviction_penalty = max(
                0, self.resource_manager.eviction_penalty - 5
            )
        return lingering_eviction_penalty

    def _calculate_loan_penalty(self):
        """Calculate a satisfaction penalty based on the city's current debt and financial health.
        The penalty is proportional to the total loan amount and increases with years."""
        loan_penalty = 0
        if self.resource_manager.total_loan_amount > 0:
            loan_penalty = (self.resource_manager.total_loan_amount / 1000) * (
                1 + self.resource_manager.years_negative_budget
            )
        return loan_penalty

    def _calculate_tax_impact(self):
        """Calculate satisfaction impact based on current tax rate.
        Higher taxes reduce satisfaction; lower taxes increase it.
        Base tax is 10. Every $1 above/below 10 affects satisfaction by a certain amount."""
        tax_impact = 0
        if self.resource_manager.tax_per_citizen > 10:
            tax_impact = -((self.resource_manager.tax_per_citizen - 10) * 2)
        elif self.resource_manager.tax_per_citizen < 10:
            tax_impact = (10 - self.resource_manager.tax_per_citizen) * 1
        return tax_impact

    def _calculate_industrial_service_imbalance_penalty(self, total_ind_jobs, total_ser_jobs):
        """Apply a penalty if there is a big imbalance between industrial and service jobs.
        A healthy city typically has a mix of both."""
        imbalance_penalty = 0
        if total_ind_jobs > 0 and total_ser_jobs > 0:
            ratio = total_ind_jobs / total_ser_jobs
            if ratio > 2.0 or ratio < 0.5:
                imbalance_penalty = 15
        elif total_ind_jobs > 0 or total_ser_jobs > 0:
            imbalance_penalty = 20
        return imbalance_penalty

    def _calculate_individual_zone_service_bonuses(self, rz, services, road_networks):
        """Calculate bonuses for a residential zone based on proximity to services."""
        from game.buildings import Police, Stadium

        for s in services:
            if not s.has_road_access or not getattr(s, "is_powered", False):
                continue

            s_networks = self._get_touched_networks(s, road_networks)
            rz_networks = self._get_touched_networks(rz, road_networks)
            if not rz_networks.intersection(s_networks):
                continue

            dist = (
                (rz.origin[0] + rz.grid_width / 2 - (s.origin[0] + s.grid_width / 2)) ** 2
                + (rz.origin[1] + rz.grid_height / 2 - (s.origin[1] + s.grid_height / 2)) ** 2
            ) ** 0.5

            if isinstance(s, Police) and dist < POLICE_RADIUS:
                rz.local_satisfaction += 10
                rz.bonuses.append("Safety Bonus (+10)")
            if isinstance(s, Stadium) and dist < STADIUM_RADIUS:
                rz.local_satisfaction += 15
                rz.bonuses.append("Stadium Bonus (+15)")

    def _calculate_individual_zone_satisfaction(
        self,
        all_zones,
        total_sat,
        road_networks,
        total_jobs_available,
        workforce,
        loan_penalty,
        tax_impact,
        imbalance_penalty,
        services,
        ind_zones,
    ):
        """Calculate satisfaction for a single residential zone based on various factors.
        No satisfaction if no road access or disconnected from road network.
        Penalties for lack of electricity.
        Penalties for severe job shortages."""
        for rz in all_zones:
            rz.local_satisfaction = total_sat

            # No satisfaction without road access
            if not rz.has_road_access:
                rz.local_satisfaction = 0
                rz.bonuses = ["No Road Access"]
                continue

            # No satisfaction if disconnected from road network
            rz_networks = self._get_touched_networks(rz, road_networks)
            if not rz_networks:
                rz.local_satisfaction = 0
                rz.bonuses = ["Disconnected Road!"]
                continue

            rz.bonuses = []

            # Severe penalty if not powered by electricity
            if not getattr(rz, "is_powered", False):
                rz.local_satisfaction -= 25
                rz.bonuses.append("No Electricity (-25)")

            # Severe job shortage penalty if less than 50% of workforce has access to jobs
            if isinstance(rz, ResZone):
                if workforce > 0 and total_jobs_available < (0.5 * workforce):
                    rz.local_satisfaction -= 15
                    rz.bonuses.append("Severe Job Shortage (-15)")

            # Apply financial penalties/bonuses
            if loan_penalty > 0:
                rz.bonuses.append(f"Debt Penalty (-{int(loan_penalty)})")

            if tax_impact < 0:
                rz.bonuses.append(f"High Taxes (-{abs(tax_impact)})")
            elif tax_impact > 0:
                rz.bonuses.append(f"Low Taxes (+{tax_impact})")

            # Apply industrial/service imbalance penalty
            if imbalance_penalty > 0:
                rz.bonuses.append(f"Imbalance Penalty (-{imbalance_penalty})")

            # Calculate bonuses from proximity to services (Stadium, Police)
            self._calculate_individual_zone_service_bonuses(rz, services, road_networks)
            if isinstance(rz, ResZone):
                self._calculate_industrial_pollution_penalty(rz, ind_zones)
                self._calculate_tree_bonus(rz)

            # Clamp satisfaction between 0 and 100
            rz.local_satisfaction = max(0, min(100, rz.local_satisfaction))

    def _calculate_tree_bonus(self, rz):
        from game.buildings import Tree

        """Calculate a satisfaction bonus for residential zones from nearby trees in line of sight.
        Trees provide bonus if they are within 3 squares
        and have a clear line of sight to ResZone."""
        rz.tree_bonus = 0
        all_trees = [e for e in self.game.entities if isinstance(e, Tree)]
        for tree in all_trees:
            # Get closest point on the ResZone to the tree
            cx = max(rz.origin[0], min(tree.origin[0], rz.origin[0] + rz.grid_width - 1))
            cy = max(rz.origin[1], min(tree.origin[1], rz.origin[1] + rz.grid_height - 1))

            # Check distance <= 3 squares (Chebyshev distance)
            if max(abs(cx - tree.origin[0]), abs(cy - tree.origin[1])) <= 3:
                # Check Line of Sight
                line = get_line(cx, cy, tree.origin[0], tree.origin[1])
                los = True
                for px, py in line:
                    if (px, py) == (cx, cy) or (px, py) == tree.origin:
                        continue
                    if self.world.buildings[px][py] is not None:
                        los = False
                        break

                if los:
                    # Base bonus * growth multiplier
                    bonus = 5 * tree.get_bonus_multiplier(self.game.current_date)
                    rz.tree_bonus += bonus

        if rz.tree_bonus > 0:
            rz.local_satisfaction += int(rz.tree_bonus)
            rz.bonuses.append(f"Nature Bonus (+{int(rz.tree_bonus)})")

    def _calculate_industrial_pollution_penalty(self, rz, ind_zones):
        """Calculate pollution penalty for a residential zone from proximity to industrial zones.
        Trees can mitigate pollution if they are between the residential and industrial zones."""
        from game.buildings import Tree

        for iz in ind_zones:
            dist = (
                (rz.origin[0] + rz.grid_width / 2 - (iz.origin[0] + iz.grid_width / 2)) ** 2
                + (rz.origin[1] + rz.grid_height / 2 - (iz.origin[1] + iz.grid_height / 2)) ** 2
            ) ** 0.5
            if dist < INDUSTRIAL_NEGATIVE_RADIUS:
                line = get_line(
                    rz.origin[0] + rz.grid_width / 2,
                    rz.origin[1] + rz.grid_height / 2,
                    iz.origin[0] + iz.grid_width / 2,
                    iz.origin[1] + iz.grid_height / 2,
                )
                forest_blocked = False
                for px, py in line:
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            nx, ny = px + dx, py + dy
                            if (
                                0 <= nx < self.world.grid_length_x
                                and 0 <= ny < self.world.grid_length_y
                            ):
                                if isinstance(self.world.buildings[nx][ny], Tree):
                                    forest_blocked = True
                                    break
                        if forest_blocked:
                            break
                    if forest_blocked:
                        break

                if forest_blocked:
                    rz.local_satisfaction -= 5
                    rz.bonuses.append("Pollution (Forest Blocked) (-5)")
                else:
                    rz.local_satisfaction -= 10
                    rz.bonuses.append("Industrial Pollution (-10)")

    def _calculate_overall_city_satisfaction(self, res_zones):
        """Calculate overall city satisfaction as the average of all residential zones."""
        if res_zones:
            self.resource_manager.satisfaction = sum(z.local_satisfaction for z in res_zones) / len(
                res_zones
            )
        else:
            self.resource_manager.satisfaction = 100  # No zones = perfect satisfaction

    def _calculate_population_growth(self, res_zones):
        """Calculate population growth/decline based on overall satisfaction and other factors."""
        logger.info(
            f"Calculating population growth. Satisfaction: {self.resource_manager.satisfaction:.2f}"
        )
        growth_potential = 0
        fluctuation = random.uniform(0.6, 1.3)
        if self.resource_manager.satisfaction > GROWTH_SATISFACTION_THRESHOLD:
            base_growth = (
                STARTER_CITY_BOOST
                if self.resource_manager.population < STARTER_POPULATION_LIMIT
                else BASE_GROWTH_RATE
            )
            bonus_growth = int(
                (self.resource_manager.satisfaction - GROWTH_SATISFACTION_THRESHOLD) / GROWTH_SCALER
            )
            raw_growth = bonus_growth + base_growth
            growth_potential = int(raw_growth * fluctuation)
        elif self.resource_manager.satisfaction < DECLINE_SATISFACTION_THRESHOLD:
            growth_potential = int(BASE_DECLINE_RATE * fluctuation)

        if growth_potential > 0:
            eligible = [
                rz
                for rz in res_zones
                if rz.occupants < rz.capacity
                and rz.has_road_access
                and getattr(rz, "is_powered", False)
            ]
            if eligible:
                actual_growth = 0
                for _ in range(growth_potential):
                    weights = [1 + getattr(rz, "tree_bonus", 0) for rz in eligible]
                    target = random.choices(eligible, weights=weights, k=1)[0]
                    target.occupants += 1
                    self.resource_manager.edu_primary += 1
                    actual_growth += 1
                    if target.occupants >= target.capacity:
                        eligible.remove(target)
                        if not eligible:
                            break
                if actual_growth > 0:
                    EventBus.publish(
                        GameEvent.NOTIFY,
                        f"City Population Growth: +{actual_growth}",
                        (100, 255, 100),
                    )
            self.resource_manager.population = sum(rz.occupants for rz in res_zones)

        # --- Apply Population Decline ---
        elif growth_potential < 0:
            if self.resource_manager.population > 0:
                EventBus.publish(
                    GameEvent.NOTIFY, f"PEOPLE ARE LEAVING: {growth_potential}", (255, 100, 100)
                )
                actual_left = 0
                for _ in range(abs(growth_potential)):
                    eligible = [rz for rz in res_zones if rz.occupants > 0]
                    if eligible:
                        target = random.choice(eligible)
                        target.occupants -= 1
                        actual_left += 1
                if actual_left > 0:
                    sec_ratio = (
                        self.resource_manager.edu_secondary / self.resource_manager.population
                    )
                    tert_ratio = (
                        self.resource_manager.edu_tertiary / self.resource_manager.population
                    )
                    sec_left = int(actual_left * sec_ratio)
                    tert_left = int(actual_left * tert_ratio)
                    self.resource_manager.edu_secondary = max(
                        0, self.resource_manager.edu_secondary - sec_left
                    )
                    self.resource_manager.edu_tertiary = max(
                        0, self.resource_manager.edu_tertiary - tert_left
                    )
                self.resource_manager.population = sum(rz.occupants for rz in res_zones)
            else:
                EventBus.publish(GameEvent.NOTIFY, "PEOPLE RE NOT COMING IN", (255, 100, 100))

    def _workplace_assignment(self, ind_zones, ser_zones, res_zones):
        """Assign workers to industrial and service zones based on road access and fill ratio.
        1. Reset all industrial and service zone occupants to 0 before assignment.
        2. Calculate a global "Fill Ratio" based on total workforce vs total job capacity.
        3. Proportionally assign workers to each zone based on its capacity and the fill ratio.
        4. Handle any rounding remainders by distributing leftover workers 1-by-1 to random zones
        with available capacity."""

        for iz in ind_zones:
            iz.occupants = 0
        for sz in ser_zones:
            sz.occupants = 0

        workforce = sum(rz.occupants for rz in res_zones)
        ind_ser_zones = [z for z in (ind_zones + ser_zones) if z.has_road_access]

        if ind_ser_zones and workforce > 0:
            total_capacity = sum(z.capacity for z in ind_ser_zones)

            assignable_workers = min(workforce, total_capacity)
            fill_ratio = assignable_workers / total_capacity

            for zone in ind_ser_zones:
                zone.occupants = int(zone.capacity * fill_ratio)

            current_assigned = sum(z.occupants for z in ind_ser_zones)
            remainder = assignable_workers - current_assigned

            if remainder > 0:
                random.shuffle(ind_ser_zones)  # Shuffle for random distribution of leftover workers
                for zone in ind_ser_zones:
                    if remainder <= 0:
                        break
                    if zone.occupants < zone.capacity:
                        zone.occupants += 1
                        remainder -= 1

    def _update_zone_images(self, ind_zones, ser_zones, res_zones):
        from game.buildings import PowerLine

        """Update the image of each zone based on its current satisfaction and occupancy."""
        for iz in ind_zones:
            iz.update_image()
        for sz in ser_zones:
            sz.update_image()
        for rz in res_zones:
            rz.update_image()
        for pl in self.game.entities:
            if isinstance(pl, PowerLine) and hasattr(pl, "update_image"):
                pl.update_image()

    def _allocate_students(self, entities, demand):
        """Assign students to schools based on available capacity and demand.
        1. Calculate total available capacity across all schools.
        2. Determine how many students can be assigned based on the fill ratio of demand vs cap.
        3. Proportionally assign students to each school based on its capacity and the fill ratio.
        4. Handle any rounding remainders by distributing leftover students
        one-by-one to random schools with available capacity."""
        total_capacity = sum(e.capacity for e in entities)
        if total_capacity == 0 or demand <= 0:
            for e in entities:
                e.occupants = 0
            return
        assignable = min(demand, total_capacity)
        fill_ratio = assignable / total_capacity

        for e in entities:
            e.occupants = int(e.capacity * fill_ratio)

        # Distribute rounding remainders
        remainder = assignable - sum(e.occupants for e in entities)
        if remainder > 0:
            random.shuffle(entities)
            for e in entities:
                if remainder <= 0:
                    break
                if e.occupants < e.capacity:
                    e.occupants += 1
                    remainder -= 1

    def _education_assignment(self):
        """Allocate citizens to educational institutions based on capacity and road access.
        1. Reset occupants for all Schools and Universities before assignment.
        2. Calculate total available capacity for Schools and Universities.
        3. Proportionally allocate students based on the fill ratio of demand vs capacity.
        4. Handle any rounding remainders by distributing leftover students
        one-by-one to random schools/universities with available capacity."""
        from game.buildings import School, University

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
        for s in schools:
            s.occupants = 0
        for u in unis:
            u.occupants = 0

        if schools and self.resource_manager.edu_primary > 0:
            self._allocate_students(schools, self.resource_manager.edu_primary)
        if unis and self.resource_manager.edu_secondary > 0:
            self._allocate_students(unis, self.resource_manager.edu_secondary)

    def _update_fire_protection(self):
        """Update fire protection status of the buildings"""
        from game.buildings import FireStation, Tree, Road, Building
        from game.setting import FIRE_STATION_RADIUS

        active_stations = [
            e for e in self.game.entities
            if isinstance(e, FireStation)
            and getattr(e, "is_powered", False)
            and getattr(e, "has_road_access", False)
        ]

        for b in self.game.entities:
            if not isinstance(b, Building) or isinstance(b, (Tree, Road, FireStation)):
                continue
            b.is_fire_protected = False
            for st in active_stations:
                dist = abs(b.origin[0] - st.origin[0]) + abs(b.origin[1] - st.origin[1])
                if dist <= FIRE_STATION_RADIUS:
                    b.is_fire_protected = True
                    break