"""Independent validator for Fly-in simulation output.

This is a *test* utility (not part of the graded deliverable). It re-reads
a map and a sequence of turn lines and confirms, from scratch, that the
movement obeys every rule in the subject: adjacency, blocked zones,
restricted two-turn transit, zone capacity and connection capacity.

Run it as::

    python tests/validator.py maps/example.txt
"""

from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Network, ZoneType  # noqa: E402
from parser import MapParser  # noqa: E402
from pathfinding import PathFinder  # noqa: E402
from simulation import SimulationResult, Simulator  # noqa: E402


class ValidationError(Exception):
    """Raised when emitted output violates a movement rule."""


def _key(a: str, b: str) -> Tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def validate(network: Network, result: SimulationResult) -> None:
    """Check that every turn of ``result`` is legal for ``network``.

    Raises:
        ValidationError: On the first rule violation found.
    """
    position: Dict[int, str] = {
        i: network.start.name for i in range(1, network.nb_drones + 1)}
    transit: Dict[int, str] = {}
    for turn, moves in enumerate(result.moves_per_turn, start=1):
        seen: Set[int] = set()
        for drone_id, _ in moves:
            if drone_id in seen:
                raise ValidationError(
                    f"turn {turn}: D{drone_id} acted more than once")
            seen.add(drone_id)
        link_use: Dict[Tuple[str, str], int] = defaultdict(int)
        arrivals_expected = dict(transit)
        for drone_id, token in moves:
            current = position[drone_id]
            if "-" in token:
                _check_launch(network, drone_id, current, token, link_use)
                _, target = token.split("-", 1)
                transit[drone_id] = target
            elif drone_id in transit:
                if token != transit[drone_id]:
                    raise ValidationError(
                        f"turn {turn}: D{drone_id} should arrive at "
                        f"{transit[drone_id]} not {token}")
                position[drone_id] = token
                del transit[drone_id]
                arrivals_expected.pop(drone_id, None)
            else:
                _check_simple(network, drone_id, current, token, turn,
                              link_use)
                position[drone_id] = token
        if arrivals_expected:
            missing = ", ".join(f"D{d}" for d in arrivals_expected)
            raise ValidationError(
                f"turn {turn}: transit drones {missing} failed to arrive")
        _check_capacity(network, position, transit, turn)
        _check_links(network, link_use, turn)
    _check_completion(network, position)


def _check_launch(
    network: Network,
    drone_id: int,
    current: str,
    token: str,
    link_use: Dict[Tuple[str, str], int],
) -> None:
    """Validate that a connection token launches a legal restricted move."""
    origin, target = token.split("-", 1)
    if origin != current:
        raise ValidationError(
            f"D{drone_id} launches from {origin} but sits in {current}")
    if target not in network.zones:
        raise ValidationError(f"D{drone_id} flies toward unknown {target}")
    if network.zones[target].zone_type is not ZoneType.RESTRICTED:
        raise ValidationError(
            f"D{drone_id} uses a connection token for non-restricted "
            f"{target}")
    if target not in network.neighbours(current):
        raise ValidationError(f"{current}-{target} is not a connection")
    link_use[_key(current, target)] += 1


def _check_simple(
    network: Network,
    drone_id: int,
    current: str,
    token: str,
    turn: int,
    link_use: Dict[Tuple[str, str], int],
) -> None:
    """Validate a single-turn move into a normal or priority zone."""
    if token not in network.zones:
        raise ValidationError(f"turn {turn}: D{drone_id} moved to unknown "
                              f"{token}")
    zone = network.zones[token]
    if not zone.zone_type.is_traversable:
        raise ValidationError(f"turn {turn}: D{drone_id} entered blocked "
                              f"{token}")
    if zone.enter_cost != 1:
        raise ValidationError(f"turn {turn}: D{drone_id} reached {token} in "
                              f"one turn but it costs {zone.enter_cost}")
    if token not in network.neighbours(current):
        raise ValidationError(f"turn {turn}: {current}-{token} is not a "
                              f"connection")
    link_use[_key(current, token)] += 1


def _check_capacity(
    network: Network,
    position: Dict[int, str],
    transit: Dict[int, str],
    turn: int,
) -> None:
    """Verify no zone exceeds its capacity at the end of a turn."""
    counts: Dict[str, int] = defaultdict(int)
    for drone_id, zone_name in position.items():
        if drone_id in transit:
            continue
        counts[zone_name] += 1
    for name, count in counts.items():
        zone = network.zones[name]
        if zone.is_unlimited:
            continue
        if count > zone.capacity:
            raise ValidationError(
                f"turn {turn}: zone {name} holds {count} drones but capacity "
                f"is {zone.capacity}")


def _check_links(
    network: Network,
    link_use: Dict[Tuple[str, str], int],
    turn: int,
) -> None:
    """Verify no connection exceeds its capacity in a turn."""
    for key, count in link_use.items():
        connection = network.connections[key]
        if count > connection.capacity:
            raise ValidationError(
                f"turn {turn}: connection {key[0]}-{key[1]} used by {count} "
                f"drones but capacity is {connection.capacity}")


def _check_completion(network: Network, position: Dict[int, str]) -> None:
    """Verify all drones finished at the end zone."""
    for drone_id, zone_name in position.items():
        if zone_name != network.end.name:
            raise ValidationError(
                f"D{drone_id} ended at {zone_name}, not the end zone")


def _validate_paths(maps: List[str]) -> int:
    """Validate the bundled maps and report the outcome."""
    failures = 0
    for path in maps:
        network = MapParser().parse_file(path)
        lanes = PathFinder(network).find_lanes()
        result = Simulator(network, lanes).run()
        try:
            validate(network, result)
            print(f"OK   {path:<28} turns={result.turns}")
        except ValidationError as error:
            failures += 1
            print(f"FAIL {path:<28} {error}")
    return failures


if __name__ == "__main__":
    targets = sys.argv[1:]
    sys.exit(1 if _validate_paths(targets) else 0)
