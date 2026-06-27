"""Graph model representing the complete drone routing network."""

from typing import Dict, List, Optional, Tuple
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

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Graph(zones={len(self.zones)}, "
            f"connections={len(self.connections)}, "
            f"drones={self.nb_drones})"
        )
