"""Pathfinding algorithm for optimal drone routing.

Uses a flow-based multi-path approach:
1. Identify K disjoint (or least-overlapping) paths from start to end.
2. Assign drones to paths based on path capacity and turn cost.
3. Schedule drone departures to avoid zone/link capacity conflicts.
4. Handle restricted zones (2-turn transit) explicitly.
"""

import heapq
from typing import Dict, List, Optional, Set, Tuple
from zone import Zone, ZoneType
from graph import Graph


class PathFinder:
    """Computes optimal routing paths through the drone network."""

    def __init__(self, graph: Graph) -> None:
        """Initialize pathfinder with the network graph.

        Args:
            graph: The drone routing network.
        """
        self.graph: Graph = graph

    def find_shortest_path(
        self,
        start: Zone,
        end: Zone,
        forbidden_zones: Optional[Set[str]] = None,
    ) -> Optional[List[Zone]]:
        """Find the minimum-cost path using Dijkstra's algorithm.

        Priority zones are preferred (lower effective cost).

        Args:
            start: Starting zone.
            end: Destination zone.
            forbidden_zones: Zone names to exclude from consideration.

        Returns:
            Ordered list of zones forming the path, or None if unreachable.
        """
        if forbidden_zones is None:
            forbidden_zones = set()

        # (cost, tiebreak, zone_name, path)
        counter = 0
        heap: List[Tuple[float, int, str, List[str]]] = [
            (0.0, counter, start.name, [start.name])
        ]
        best: Dict[str, float] = {start.name: 0.0}

        while heap:
            cost, _, current_name, path = heapq.heappop(heap)
            current = self.graph.zones[current_name]

            if current is end:
                return [self.graph.zones[n] for n in path]

            if cost > best.get(current_name, 1e18):
                continue

            for neighbor, _ in self.graph.get_neighbors(current):
                if neighbor.name in forbidden_zones and neighbor is not end:
                    continue
                if neighbor.name in path:  # Avoid cycles
                    continue

                # Priority zones have same cost but are preferred via
                # tiebreaking
                move_cost: float = float(neighbor.zone_type.movement_cost)
                # Slight negative bias for priority to prefer them
                if neighbor.zone_type == ZoneType.PRIORITY:
                    move_cost = 0.9

                new_cost = cost + move_cost
                if new_cost < best.get(neighbor.name, 1e18):
                    best[neighbor.name] = new_cost
                    counter += 1
                    heapq.heappush(
                        heap,
                        (
                            new_cost,
                            counter,
                            neighbor.name,
                            path + [neighbor.name]
                        )
                    )

        return None

    def find_k_best_paths(
        self,
        start: Zone,
        end: Zone,
        k: int,
    ) -> List[List[Zone]]:
        """Find k paths with varied routes using zone penalty method.

        Args:
            start: Starting zone.
            end: Destination zone.
            k: Number of paths to find.

        Returns:
            List of up to k paths, ordered by base cost.
        """
        paths: List[List[Zone]] = []
        zone_usage: Dict[str, float] = {}
        seen_signatures: Set[Tuple[str, ...]] = set()

        # Try with progressively higher penalties
        for attempt in range(k * 3):
            if len(paths) >= k:
                break
            counter = 0
            heap: List[Tuple[float, int, str, List[str]]] = [
                (0.0, counter, start.name, [start.name])
            ]
            best: Dict[str, float] = {start.name: 0.0}
            found: Optional[List[Zone]] = None

            penalty_factor = 4.0 + attempt * 2.0

            while heap:
                cost, _, current_name, path = heapq.heappop(heap)
                current = self.graph.zones[current_name]

                if current is end:
                    found = [self.graph.zones[n] for n in path]
                    break

                if cost > best.get(current_name, 1e18):
                    continue

                for neighbor, _ in self.graph.get_neighbors(current):
                    if neighbor.name in path:
                        continue

                    move_cost = float(neighbor.zone_type.movement_cost)
                    if neighbor.zone_type == ZoneType.PRIORITY:
                        move_cost = 0.9

                    if neighbor is not end and neighbor is not start:
                        penalty = zone_usage.get(
                            neighbor.name, 0.0) * penalty_factor
                        move_cost += penalty

                    new_cost = cost + move_cost
                    if new_cost < best.get(neighbor.name, 1e18):
                        best[neighbor.name] = new_cost
                        counter += 1
                        heapq.heappush(
                            heap,
                            (
                                new_cost,
                                counter,
                                neighbor.name,
                                path + [neighbor.name]
                            )
                        )

            if found is None:
                break

            sig = tuple(z.name for z in found)
            if sig in seen_signatures:
                # Bump usage and try again with higher penalty
                for z in found[1:-1]:
                    zone_usage[z.name] = zone_usage.get(z.name, 0.0) + 0.5
                continue

            seen_signatures.add(sig)
            paths.append(found)
            for zone in found[1:-1]:
                zone_usage[zone.name] = zone_usage.get(zone.name, 0.0) + 1.0

        return paths

    def path_true_cost(self, path: List[Zone]) -> int:
        """Calculate exact turn cost (using integer movement costs).

        Args:
            path: Ordered list of zones.

        Returns:
            Total turns required to traverse the path.
        """
        total = 0
        for i in range(1, len(path)):
            total += path[i].zone_type.movement_cost
        return total

    def bottleneck_capacity(self, path: List[Zone]) -> int:
        """Find the minimum capacity along a path (throughput limit).

        Considers both zone max_drones and connection max_link_capacity.

        Args:
            path: Ordered list of zones.

        Returns:
            Minimum capacity value along the path.
        """
        min_cap = 999999
        for zone in path:
            if not zone.is_start and not zone.is_end:
                min_cap = min(min_cap, zone.max_drones)

        for i in range(len(path) - 1):
            conn = self.graph.get_connection(path[i], path[i + 1])
            if conn:
                min_cap = min(min_cap, conn.max_link_capacity)

        return min_cap
