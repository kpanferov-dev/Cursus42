"""Zone model representing a node in the drone network graph."""

from enum import Enum
from typing import Optional


class ZoneType(Enum):
    """Types of zones with associated movement costs."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def movement_cost(self) -> int:
        """Return the number of turns required to enter this zone type."""
        if self == ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def is_accessible(self) -> bool:
        """Return whether drones can enter this zone."""
        return self != ZoneType.BLOCKED


class Zone:
    """Represents a zone (node) in the drone routing network."""

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: Optional[str] = None,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        """Initialize a zone.

        Args:
            name: Unique identifier for this zone.
            x: X coordinate.
            y: Y coordinate.
            zone_type: Type determining movement cost and accessibility.
            color: Optional color for visual representation.
            max_drones: Maximum drones allowed simultaneously.
            is_start: Whether this is the starting hub.
            is_end: Whether this is the ending hub.
        """
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: ZoneType = zone_type
        self.color: Optional[str] = color
        self.max_drones: int = max_drones
        self.is_start: bool = is_start
        self.is_end: bool = is_end
        self._current_drones: int = 0

    @property
    def current_drones(self) -> int:
        """Return current drone count in this zone."""
        return self._current_drones

    @current_drones.setter
    def current_drones(self, value: int) -> None:
        """Set current drone count."""
        self._current_drones = value

    @property
    def has_capacity(self) -> bool:
        """Return whether zone can accept at least one more drone."""
        if self.is_start or self.is_end:
            return True
        return self._current_drones < self.max_drones

    def available_capacity(self) -> int:
        """Return how many more drones can enter this zone."""
        if self.is_start or self.is_end:
            return 999999
        return max(0, self.max_drones - self._current_drones)

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Zone({self.name}, type={self.zone_type.value}, "
            f"pos=({self.x},{self.y}), drones={self._current_drones}/"
            f"{self.max_drones})")
