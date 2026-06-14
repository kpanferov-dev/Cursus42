"""Domain model for the Fly-in drone routing project.

This module defines the core, framework-agnostic data structures used
throughout the project: the different :class:`ZoneType` values, an
individual :class:`Zone`, a bidirectional :class:`Connection` and the
:class:`Network` that ties zones and connections together into a graph.

No graph-helper libraries are used; all graph logic is implemented by
hand as required by the subject.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterator, List, Optional, Tuple

# A capacity sentinel used for the start and end zones, which may hold
# an unlimited number of drones at once.
UNLIMITED: int = -1


class ZoneType(Enum):
    """The four kinds of zone a drone may encounter.

    The value attached to each member is the movement cost, expressed in
    simulation turns, of *entering* a zone of that type. ``BLOCKED`` zones
    can never be entered and therefore have no finite cost.
    """

    NORMAL = "normal"
    PRIORITY = "priority"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"

    @property
    def cost(self) -> int:
        """Return the turn cost of entering a zone of this type.

        Returns:
            The number of turns required to move into the zone. Blocked
            zones return ``0`` because they are never traversed; callers
            must check :meth:`is_traversable` first.
        """
        if self is ZoneType.RESTRICTED:
            return 2
        return 1

    @property
    def is_traversable(self) -> bool:
        """Return whether a drone may ever occupy a zone of this type."""
        return self is not ZoneType.BLOCKED

    @property
    def is_priority(self) -> bool:
        """Return whether this type should be preferred during routing."""
        return self is ZoneType.PRIORITY

    @classmethod
    def from_string(cls, raw: str) -> "ZoneType":
        """Build a :class:`ZoneType` from its textual representation.

        Args:
            raw: The zone type as written in a map file.

        Returns:
            The matching :class:`ZoneType` member.

        Raises:
            ValueError: If ``raw`` is not a recognised zone type.
        """
        for member in cls:
            if member.value == raw:
                return member
        valid = ", ".join(member.value for member in cls)
        raise ValueError(f"unknown zone type '{raw}' (expected one of {valid})")


@dataclass
class Zone:
    """A single location in the network.

    Attributes:
        name: Unique identifier of the zone.
        x: Integer x coordinate.
        y: Integer y coordinate.
        zone_type: The :class:`ZoneType` of the zone.
        color: Optional single-word colour used for display.
        capacity: Maximum number of drones allowed at the same time.
            Equal to :data:`UNLIMITED` for the start and end zones.
        is_start: Whether this is the unique start zone.
        is_end: Whether this is the unique end zone.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: Optional[str] = None
    capacity: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def enter_cost(self) -> int:
        """Return the number of turns needed to enter this zone."""
        return self.zone_type.cost

    @property
    def is_unlimited(self) -> bool:
        """Return whether the zone has unlimited capacity."""
        return self.capacity == UNLIMITED

    def has_room_for(self, occupants: int) -> bool:
        """Return whether ``occupants`` extra drones could fit.

        Args:
            occupants: The number of drones that would occupy the zone.

        Returns:
            ``True`` if the zone is unlimited or ``occupants`` does not
            exceed its capacity.
        """
        if self.is_unlimited:
            return True
        return occupants <= self.capacity


@dataclass
class Connection:
    """A bidirectional link between two zones.

    Attributes:
        first: Name of one endpoint zone.
        second: Name of the other endpoint zone.
        capacity: Maximum number of drones that may traverse the link at
            the same time (``max_link_capacity``).
    """

    first: str
    second: str
    capacity: int = 1

    @property
    def key(self) -> Tuple[str, str]:
        """Return an order-independent key identifying the connection."""
        return tuple(sorted((self.first, self.second)))  # type: ignore[return-value]

    def other(self, name: str) -> str:
        """Return the endpoint that is not ``name``.

        Args:
            name: One of the two endpoint names.

        Returns:
            The opposite endpoint.

        Raises:
            KeyError: If ``name`` is not an endpoint of this connection.
        """
        if name == self.first:
            return self.second
        if name == self.second:
            return self.first
        raise KeyError(f"'{name}' is not an endpoint of this connection")


@dataclass
class Network:
    """A graph of zones joined by connections.

    Attributes:
        nb_drones: Number of drones to route from start to end.
        zones: Mapping of zone name to :class:`Zone`.
        connections: Mapping of order-independent key to :class:`Connection`.
        adjacency: Mapping of zone name to the list of neighbour names.
    """

    nb_drones: int = 0
    zones: Dict[str, Zone] = field(default_factory=dict)
    connections: Dict[Tuple[str, str], Connection] = field(
        default_factory=dict)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)
    _start: Optional[str] = None
    _end: Optional[str] = None

    def add_zone(self, zone: Zone) -> None:
        """Register a new zone in the network.

        Args:
            zone: The zone to add.

        Raises:
            KeyError: If a zone with the same name already exists.
        """
        if zone.name in self.zones:
            raise KeyError(f"duplicate zone name '{zone.name}'")
        self.zones[zone.name] = zone
        self.adjacency.setdefault(zone.name, [])
        if zone.is_start:
            self._start = zone.name
        if zone.is_end:
            self._end = zone.name

    def add_connection(self, connection: Connection) -> None:
        """Register a new bidirectional connection.

        Args:
            connection: The connection to add.

        Raises:
            KeyError: If either endpoint is unknown or the connection is a
                duplicate of an existing one.
        """
        for endpoint in (connection.first, connection.second):
            if endpoint not in self.zones:
                raise KeyError(f"connection refers to unknown zone "
                               f"'{endpoint}'")
        if connection.key in self.connections:
            raise KeyError(f"duplicate connection "
                           f"'{connection.first}-{connection.second}'")
        self.connections[connection.key] = connection
        self.adjacency[connection.first].append(connection.second)
        self.adjacency[connection.second].append(connection.first)

    @property
    def start(self) -> Zone:
        """Return the start zone.

        Raises:
            ValueError: If no start zone has been defined.
        """
        if self._start is None:
            raise ValueError("network has no start zone")
        return self.zones[self._start]

    @property
    def end(self) -> Zone:
        """Return the end zone.

        Raises:
            ValueError: If no end zone has been defined.
        """
        if self._end is None:
            raise ValueError("network has no end zone")
        return self.zones[self._end]

    def neighbours(self, name: str) -> List[str]:
        """Return the names of zones adjacent to ``name``."""
        return self.adjacency.get(name, [])

    def connection_between(self, first: str, second: str) -> Connection:
        """Return the connection joining two zones.

        Args:
            first: One endpoint name.
            second: The other endpoint name.

        Returns:
            The :class:`Connection` linking the two zones.

        Raises:
            KeyError: If no such connection exists.
        """
        key: Tuple[str, str] = tuple(sorted((first, second)))  # type: ignore
        return self.connections[key]

    def __iter__(self) -> Iterator[Zone]:
        """Iterate over all zones in the network."""
        return iter(self.zones.values())
