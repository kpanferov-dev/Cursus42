"""Graph model representing the complete drone routing network."""

from typing import Dict, List, Optional, Set, Tuple
from zone import Zone
from connection import Connection


class Graph:
    """Represents the drone routing network as an adjacency structure."""

    def __init__(self) -> None:
        """Initialize an empty graph."""
        self.zones: Dict[str, Zone] = {}
        self.connections: List[Connection] = []
        self._adjacency: Dict[str, List[Connection]] = {}
        self.start_zone: Optional[Zone] = None
        self.end_zone: Optional[Zone] = None
        self.nb_drones: int = 0

    def add_zone(self, zone: Zone) -> None:
        """Add a zone to the graph.

        Args:
            zone: The zone to add.

        Raises:
            ValueError: If a zone with the same name already exists.
        """
        if zone.name in self.zones:
            raise ValueError(
                f"Zone '{zone.name}' already exists in the graph.")
        self.zones[zone.name] = zone
        self._adjacency[zone.name] = []
        if zone.is_start:
            self.start_zone = zone
        if zone.is_end:
            self.end_zone = zone

    def add_connection(self, connection: Connection) -> None:
        """Add a connection (edge) to the graph.

        Args:
            connection: The connection to add.

        Raises:
            ValueError: If duplicate connection detected.
        """
        for existing in self.connections:
            if existing.connects(connection.zone_a, connection.zone_b):
                raise ValueError(
                    f"Duplicate connection: {connection.zone_a.name} "
                    f"<-> {connection.zone_b.name}"
                )
        self.connections.append(connection)
        self._adjacency[connection.zone_a.name].append(connection)
        self._adjacency[connection.zone_b.name].append(connection)

    def get_zone(self, name: str) -> Optional[Zone]:
        """Retrieve a zone by name.

        Args:
            name: Zone identifier.

        Returns:
            Zone instance or None if not found.
        """
        return self.zones.get(name)

    def get_neighbors(self, zone: Zone) -> List[Tuple[Zone, Connection]]:
        """Return accessible neighboring zones with their connections.

        Args:
            zone: Source zone.

        Returns:
            List of (neighbor_zone, connection) tuples.
        """
        neighbors: List[Tuple[Zone, Connection]] = []
        for conn in self._adjacency.get(zone.name, []):
            neighbor = conn.other_zone(zone)
            if neighbor.zone_type.is_accessible:
                neighbors.append((neighbor, conn))
        return neighbors

    def get_connection(
            self,
            zone_a: Zone,
            zone_b: Zone) -> Optional[Connection]:
        """Find the connection between two zones.

        Args:
            zone_a: First zone.
            zone_b: Second zone.

        Returns:
            Connection instance or None.
        """
        for conn in self._adjacency.get(zone_a.name, []):
            if conn.connects(zone_a, zone_b):
                return conn
        return None

    def find_all_paths(
        self,
        start: Zone,
        end: Zone,
        max_depth: int = 100,
    ) -> List[List[Zone]]:
        """Find all simple paths from start to end using DFS.

        Args:
            start: Starting zone.
            end: Target zone.
            max_depth: Maximum path length to prevent infinite loops.

        Returns:
            List of paths, each being an ordered list of zones.
        """
        all_paths: List[List[Zone]] = []
        visited: Set[str] = set()

        def dfs(current: Zone, path: List[Zone]) -> None:
            if len(path) > max_depth:
                return
            if current is end:
                all_paths.append(list(path))
                return
            visited.add(current.name)
            for neighbor, _ in self.get_neighbors(current):
                if neighbor.name not in visited:
                    path.append(neighbor)
                    dfs(neighbor, path)
                    path.pop()
            visited.discard(current.name)

        dfs(start, [start])
        return all_paths

    def shortest_path(
        self, start: Zone, end: Zone
    ) -> Optional[List[Zone]]:
        """Find the shortest path by turn cost using Dijkstra's algorithm.

        Args:
            start: Starting zone.
            end: Target zone.

        Returns:
            Ordered list of zones, or None if unreachable.
        """
        import heapq

        # (cost, zone_name, path)
        heap: List[Tuple[int, str, List[str]]] = [
            (0, start.name, [start.name])]
        best: Dict[str, int] = {start.name: 0}

        while heap:
            cost, current_name, path = heapq.heappop(heap)
            current = self.zones[current_name]

            if current is end:
                return [self.zones[n] for n in path]

            if cost > best.get(current_name, 999999):
                continue

            for neighbor, _ in self.get_neighbors(current):
                new_cost = cost + neighbor.zone_type.movement_cost
                if new_cost < best.get(neighbor.name, 999999):
                    best[neighbor.name] = new_cost
                    heapq.heappush(
                        heap,
                        (new_cost, neighbor.name, path + [neighbor.name]),
                    )

        return None

    def path_cost(self, path: List[Zone]) -> int:
        """Calculate total turn cost for a given path.

        Args:
            path: Ordered list of zones.

        Returns:
            Sum of movement costs for all transitions.
        """
        total = 0
        for i in range(1, len(path)):
            total += path[i].zone_type.movement_cost
        return total

    def find_disjoint_paths(
        self, start: Zone, end: Zone, num_paths: int
    ) -> List[List[Zone]]:
        """Find multiple paths with minimal zone
        overlap using cost-based search.

        Uses a greedy approach: repeatedly find shortest paths while
        penalizing already-used zones.

        Args:
            start: Starting zone.
            end: Target zone.
            num_paths: Desired number of paths.

        Returns:
            List of paths (may be fewer than num_paths if topology limits).
        """
        import heapq

        used_zones: Dict[str, int] = {}
        result_paths: List[List[Zone]] = []

        for _ in range(num_paths):
            # Weighted Dijkstra with penalty for used zones
            heap: List[Tuple[float, str, List[str]]] = [
                (0.0, start.name, [start.name])
            ]
            best: Dict[str, float] = {start.name: 0.0}

            found_path: Optional[List[Zone]] = None

            while heap:
                cost, current_name, path = heapq.heappop(heap)
                current = self.zones[current_name]

                if current is end:
                    found_path = [self.zones[n] for n in path]
                    break

                if cost > best.get(current_name, 999999.0):
                    continue

                for neighbor, _ in self.get_neighbors(current):
                    if neighbor.name in path:  # Avoid cycles
                        continue
                    penalty = used_zones.get(neighbor.name, 0) * 10.0
                    new_cost = (
                        cost
                        + neighbor.zone_type.movement_cost
                        + penalty
                    )
                    if new_cost < best.get(neighbor.name, 999999.0):
                        best[neighbor.name] = new_cost
                        heapq.heappush(
                            heap,
                            (new_cost, neighbor.name, path + [neighbor.name]),
                        )

            if found_path is None:
                break

            result_paths.append(found_path)
            for zone in found_path[1:-1]:  # Don't penalize start/end
                used_zones[zone.name] = used_zones.get(zone.name, 0) + 1

        return result_paths

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Graph(zones={len(self.zones)}, "
            f"connections={len(self.connections)}, "
            f"drones={self.nb_drones})"
        )
