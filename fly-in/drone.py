"""Drone model representing an individual drone in the simulation."""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from zone import Zone
    from connection import Connection


class DroneState(Enum):
    """Possible states for a drone during simulation."""

    WAITING = "waiting"
    MOVING = "moving"
    IN_TRANSIT = "in_transit"  # Traversing a restricted zone (2-turn move)
    DELIVERED = "delivered"


class Drone:
    """Represents a single drone navigating the network."""

    def __init__(self, drone_id: int, start_zone: "Zone") -> None:
        """Initialize a drone at the start zone.

        Args:
            drone_id: Unique numeric identifier.
            start_zone: The zone where this drone begins.
        """
        self.drone_id: int = drone_id
        self.current_zone: "Zone" = start_zone
        self.state: DroneState = DroneState.WAITING
        self.path: List["Zone"] = []
        self.path_index: int = 0

        # For restricted zone 2-turn transit
        self.transit_destination: Optional["Zone"] = None
        self.transit_connection: Optional["Connection"] = None
        self.transit_turns_remaining: int = 0

    @property
    def name(self) -> str:
        """Return formatted drone identifier string."""
        return f"D{self.drone_id}"

    @property
    def is_delivered(self) -> bool:
        """Return whether drone has reached its destination."""
        return self.state == DroneState.DELIVERED

    @property
    def is_in_transit(self) -> bool:
        """Return whether drone is mid-transit through restricted zone."""
        return self.state == DroneState.IN_TRANSIT

    def set_path(self, path: List["Zone"]) -> None:
        """Assign a navigation path to this drone.

        Args:
            path: Ordered list of zones from current to destination.
        """
        self.path = path
        self.path_index = 0

    def next_zone(self) -> Optional["Zone"]:
        """Return the next zone in this drone's planned path.

        Returns:
            Next zone, or None if path is empty or exhausted.
        """
        if not self.path:
            return None
        next_idx = self.path_index + 1
        if next_idx < len(self.path):
            return self.path[next_idx]
        return None

    def advance_path(self) -> None:
        """Move to the next position in the planned path."""
        self.path_index += 1

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"Drone({self.name}, zone={self.current_zone.name}, "
            f"state={self.state.value})"
        )