"""Turn-by-turn simulation engine for the Fly-in project.

The :class:`Simulator` is the authoritative component: regardless of what
the pathfinder proposes, the simulator only ever emits moves that respect
every occupancy, capacity and timing rule from the subject. Drones are
assigned to lanes with a balanced greedy distribution and then advanced
one turn at a time.
"""

from __future__ import annotations

import heapq
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from models import Network
from pathfinding import Lane

# Hard ceiling on turns to guarantee termination even on a pathological
# map; a correct run finishes far below this.
_MAX_TURNS: int = 100_000


@dataclass
class _Transit:
    """State of a drone crossing a connection toward a restricted zone."""

    token: str
    key: Tuple[str, str]
    arrive_turn: int
    target_index: int


@dataclass
class Drone:
    """A single drone following an assigned lane.

    Attributes:
        identifier: 1-based drone number used in the output.
        lane: The :class:`~pathfinding.Lane` the drone follows.
        position: Index of the drone's current zone within the lane.
        transit: In-flight state, or ``None`` when the drone sits in a zone.
        delivered: Whether the drone has reached the end zone.
    """

    identifier: int
    lane: Lane
    position: int = 0
    transit: Optional[_Transit] = None
    delivered: bool = False

    @property
    def current_zone(self) -> str:
        """Return the name of the zone the drone currently occupies."""
        return self.lane.zones[self.position]


@dataclass
class SimulationResult:
    """Outcome of a simulation run.

    Attributes:
        lines: The formatted output line for each turn.
        moves_per_turn: For each turn, the ``(drone_id, token)`` pairs.
        turns: Total number of turns used.
    """

    lines: List[str] = field(default_factory=list)
    moves_per_turn: List[List[Tuple[int, str]]] = field(default_factory=list)

    @property
    def turns(self) -> int:
        """Return the number of turns the simulation took."""
        return len(self.lines)


class Simulator:
    """Schedule drones along lanes and produce the move-by-move output."""

    def __init__(self, network: Network, lanes: List[Lane]) -> None:
        """Initialise the simulator.

        Args:
            network: The network being routed.
            lanes: Candidate lanes from the pathfinder (non-empty).

        Raises:
            ValueError: If no lanes are supplied.
        """
        if not lanes:
            raise ValueError("at least one lane is required")
        self._network = network
        self._lanes = lanes
        self._drones = self._assign_drones()
        self._occupancy: Dict[str, int] = defaultdict(int)
        self._inflight: Dict[Tuple[str, str], int] = defaultdict(int)
        self._occupancy[network.start.name] = network.nb_drones

    def _assign_drones(self) -> List[Drone]:
        """Distribute drones across lanes to balance finishing turns.

        Each drone is placed on the lane that currently promises the
        earliest completion, estimated as ``lane.cost + load``. This is
        the classic allocation that minimises the makespan when one drone
        can enter a lane per turn.
        """
        load = [0] * len(self._lanes)
        heap: List[Tuple[int, int]] = [
            (lane.cost, i) for i, lane in enumerate(self._lanes)]
        heapq.heapify(heap)
        drones: List[Drone] = []
        for identifier in range(1, self._network.nb_drones + 1):
            estimate, lane_index = heapq.heappop(heap)
            drones.append(Drone(identifier=identifier,
                                lane=self._lanes[lane_index]))
            load[lane_index] += 1
            heapq.heappush(
                heap, (self._lanes[lane_index].cost + load[lane_index],
                       lane_index))
        return drones

    def run(self) -> SimulationResult:
        """Run the full simulation until every drone is delivered.

        Returns:
            A :class:`SimulationResult` with one line per turn.

        Raises:
            RuntimeError: If the simulation fails to make progress, which
                would indicate an unexpected deadlock.
        """
        result = SimulationResult()
        turn = 0
        while not self._all_delivered():
            turn += 1
            if turn > _MAX_TURNS:
                raise RuntimeError("simulation exceeded the turn ceiling")
            moves = self._step(turn)
            if not moves and not self._all_delivered():
                raise RuntimeError("simulation deadlocked")
            if moves:
                moves.sort(key=lambda pair: pair[0])
                result.moves_per_turn.append(moves)
                result.lines.append(
                    " ".join(f"D{i}-{token}" for i, token in moves))
        return result

    def _all_delivered(self) -> bool:
        """Return whether every drone has reached the end zone."""
        return all(drone.delivered for drone in self._drones)

    def _step(self, turn: int) -> List[Tuple[int, str]]:
        """Advance the simulation by exactly one turn.

        Args:
            turn: The 1-based number of the turn being played.

        Returns:
            The ``(drone_id, token)`` movements that happened this turn.
        """
        moves: List[Tuple[int, str]] = []
        arrived = self._resolve_arrivals(turn, moves)
        committed = self._resolve_moves(turn, moves, arrived)
        self._break_rotation(turn, moves, committed | arrived)
        return moves

    def _resolve_arrivals(
        self, turn: int, moves: List[Tuple[int, str]]
    ) -> Set[int]:
        """Complete every restricted-zone transit due to arrive this turn.

        A drone that arrives this turn has already used its single action
        and must not move again, so its id is returned for exclusion.
        """
        arrived: Set[int] = set()
        for drone in self._drones:
            transit = drone.transit
            if transit is None or transit.arrive_turn != turn:
                continue
            self._inflight[transit.key] -= 1
            drone.position = transit.target_index
            drone.transit = None
            if drone.position == drone.lane.hops:
                drone.delivered = True
            moves.append((drone.identifier, drone.current_zone))
            arrived.add(drone.identifier)
        return arrived

    def _resolve_moves(
        self, turn: int, moves: List[Tuple[int, str]], exclude: Set[int]
    ) -> Set[int]:
        """Advance drones along their lanes with a greedy fixpoint pass."""
        committed_conn: Dict[Tuple[str, str], int] = defaultdict(int)
        committed: Set[int] = set()
        progressing = True
        active = self._active_drones(exclude)
        while progressing:
            progressing = False
            for drone in active:
                if drone.identifier in committed:
                    continue
                if self._try_advance(drone, turn, committed_conn, moves):
                    committed.add(drone.identifier)
                    progressing = True
        return committed

    def _active_drones(self, exclude: Set[int]) -> List[Drone]:
        """Return movable drones ordered from closest-to-goal first."""
        active = [drone for drone in self._drones
                  if not drone.delivered and drone.transit is None
                  and drone.identifier not in exclude]
        active.sort(key=lambda drone: (-drone.position, drone.identifier))
        return active

    def _try_advance(
        self,
        drone: Drone,
        turn: int,
        committed_conn: Dict[Tuple[str, str], int],
        moves: List[Tuple[int, str]],
    ) -> bool:
        """Attempt to move one drone one step along its lane.

        Returns:
            ``True`` if the drone moved (or launched a transit) this turn.
        """
        current = drone.current_zone
        target = drone.lane.zones[drone.position + 1]
        key = self._key(current, target)
        connection = self._network.connection_between(current, target)
        used = self._inflight[key] + committed_conn[key]
        if used >= connection.capacity:
            return False
        target_zone = self._network.zones[target]
        if not self._has_room(target):
            return False
        if target_zone.enter_cost == 1:
            self._commit_simple(drone, current, target, key,
                                committed_conn, moves)
        else:
            self._commit_transit(drone, current, target, key, turn, moves)
        return True

    def _commit_simple(
        self,
        drone: Drone,
        current: str,
        target: str,
        key: Tuple[str, str],
        committed_conn: Dict[Tuple[str, str], int],
        moves: List[Tuple[int, str]],
    ) -> None:
        """Perform a single-turn move into a normal or priority zone."""
        self._occupancy[current] -= 1
        self._occupancy[target] += 1
        committed_conn[key] += 1
        drone.position += 1
        if drone.position == drone.lane.hops:
            drone.delivered = True
        moves.append((drone.identifier, target))

    def _commit_transit(
        self,
        drone: Drone,
        current: str,
        target: str,
        key: Tuple[str, str],
        turn: int,
        moves: List[Tuple[int, str]],
    ) -> None:
        """Launch a two-turn move toward a restricted zone."""
        self._occupancy[current] -= 1
        self._occupancy[target] += 1
        self._inflight[key] += 1
        token = f"{current}-{target}"
        drone.transit = _Transit(
            token=token,
            key=key,
            arrive_turn=turn + 1,
            target_index=drone.position + 1,
        )
        moves.append((drone.identifier, token))

    def _break_rotation(
        self,
        turn: int,
        moves: List[Tuple[int, str]],
        committed: Set[int],
    ) -> None:
        """Resolve a cyclic wait where drones swap places simultaneously.

        Such cycles can only involve single-turn moves; restricted
        transits already reserve their destination and never wait. Every
        zone in the cycle keeps the same occupancy, so the rotation is
        always capacity-safe; only connection capacity must be checked.
        """
        waiting = self._active_drones(committed)
        position_of = {drone.current_zone: drone for drone in waiting}
        for drone in waiting:
            if drone.identifier in committed:
                continue
            cycle = self._find_cycle(drone, position_of, committed)
            if cycle is None:
                continue
            for member in cycle:
                target = member.lane.zones[member.position + 1]
                member.position += 1
                committed.add(member.identifier)
                moves.append((member.identifier, target))

    def _find_cycle(
        self,
        start: Drone,
        position_of: Dict[str, Drone],
        committed: Set[int],
    ) -> Optional[List[Drone]]:
        """Return a rotation cycle of single-turn movers, if one exists."""
        chain: List[Drone] = []
        seen = set()
        drone: Optional[Drone] = start
        while drone is not None and drone.identifier not in committed:
            target = drone.lane.zones[drone.position + 1]
            target_zone = self._network.zones[target]
            if target_zone.enter_cost != 1:
                return None
            connection = self._network.connection_between(
                drone.current_zone, target)
            if connection.capacity < 1:
                return None
            if drone.identifier in seen:
                index = next(i for i, member in enumerate(chain)
                             if member.identifier == drone.identifier)
                return chain[index:]
            seen.add(drone.identifier)
            chain.append(drone)
            drone = position_of.get(target)
        return None

    def _has_room(self, name: str) -> bool:
        """Return whether ``name`` can accept one more drone."""
        zone = self._network.zones[name]
        if zone.is_unlimited:
            return True
        return self._occupancy[name] < zone.capacity

    @staticmethod
    def _key(first: str, second: str) -> Tuple[str, str]:
        """Return the order-independent key of a connection."""
        return tuple(sorted((first, second)))  # type: ignore[return-value]
