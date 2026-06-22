"""Connection model representing an edge in the drone network graph."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zone import Zone


class Connection:
    """Represents a bidirectional connection (edge) between two zones."""

    def __init__(
        self,
        zone_a: "Zone",
        zone_b: "Zone",
        max_link_capacity: int = 1,
    ) -> None:
        """Initialize a connection between two zones.

        Args:
            zone_a: First zone endpoint.
            zone_b: Second zone endpoint.
            max_link_capacity: Max drones traversing simultaneously.
        """
        self.zone_a: "Zone" = zone_a
        self.zone_b: "Zone" = zone_b
        self.max_link_capacity: int = max_link_capacity
        self._current_usage: int = 0

    @property
    def name(self) -> str:
        """Return canonical name for this connection."""
        return f"{self.zone_a.name}-{self.zone_b.name}"

    @property
    def current_usage(self) -> int:
        """Return current number of drones traversing."""
        return self._current_usage

    @current_usage.setter
    def current_usage(self, value: int) -> None:
        """Set current usage."""
        self._current_usage = value

    @property
    def has_capacity(self) -> bool:
        """Return whether connection can accept more drones."""
        return self._current_usage < self.max_link_capacity

    def available_capacity(self) -> int:
        """Return remaining traversal capacity."""
        return max(0, self.max_link_capacity - self._current_usage)

    def other_zone(self, zone: "Zone") -> "Zone":
        """Return the zone on the other end of this connection.

        Args:
            zone: One endpoint of the connection.

        Returns:
            The other endpoint.

        Raises:
            ValueError: If the given zone is not part of this connection.
        """
        if zone is self.zone_a:
            return self.zone_b
        elif zone is self.zone_b:
            return self.zone_a
        else:
            raise ValueError(
                f"Zone {zone.name} is not part of connection {self.name}")

    def connects(self, zone_a: "Zone", zone_b: "Zone") -> bool:
        """Check if this connection links the two given zones (in any order).

        Args:
            zone_a: First zone.
            zone_b: Second zone.

        Returns:
            True if this connection links both zones.
        """
        return (
            (self.zone_a is zone_a and self.zone_b is zone_b)
            or (self.zone_a is zone_b and self.zone_b is zone_a)
        )

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Connection({self.zone_a.name} <-> {self.zone_b.name}, "
            f"cap={self.max_link_capacity}, usage={self._current_usage})"
        )