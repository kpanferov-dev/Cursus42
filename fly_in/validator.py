"""Output validator — verifies a simulation transcript respects all rules."""

from typing import Dict, List, Optional, Set, Tuple
from graph import Graph
from zone import ZoneType
from connection import Connection
from map_parser import MapParser


class ValidationError(Exception):
    """Raised when a simulation output violates the spec."""

    pass


def validate(graph: Graph, turn_log: List[List[str]]) -> Tuple[bool, str]:
    """Validate a simulation transcript against spec rules.

    Args:
        graph: The map graph.
        turn_log: List of turns, each a list of tokens like 'D1-zone'.

    Returns:
        Tuple of (is_valid, message). Message describes the issue.
    """
    assert graph.start_zone is not None
    assert graph.end_zone is not None

    nb = graph.nb_drones
    # drone_id -> current zone name OR connection name (if in transit)
    drone_pos: Dict[int, str] = {
        i + 1: graph.start_zone.name for i in range(nb)}
    # drone_id -> True if in transit (occupies a link, not a zone)
    in_transit: Dict[int, bool] = {i + 1: False for i in range(nb)}
    # drone_id -> destination zone name (if in transit)
    transit_dest: Dict[int, str] = {}
    # delivered drones
    delivered: Set[int] = set()

    for turn_num, tokens in enumerate(turn_log, start=1):
        # Each drone may appear at most once
        seen_drones: Set[int] = set()

        # Track per-turn capacity usage
        zone_arrivals: Dict[str, int] = {}
        zone_departures: Dict[str, int] = {}
        link_use: Dict[str, int] = {}

        # Parse all tokens for this turn
        actions: List[Tuple[int, str]] = []
        for tok in tokens:
            if not tok.startswith("D"):
                return False, (
                    f"Turn {turn_num}: token '{tok}' must start with 'D'"
                )
            try:
                dash = tok.index("-")
            except ValueError:
                return False, f"Turn {turn_num}: token '{tok}' missing '-'"
            drone_str = tok[:dash]
            target = tok[dash + 1:]
            try:
                drone_id = int(drone_str[1:])
            except ValueError:
                return False, f"Turn {turn_num}: bad drone id '{drone_str}'"

            if drone_id in seen_drones:
                return False, (
                    f"Turn {turn_num}: drone {drone_id} appears twice"
                )
            seen_drones.add(drone_id)

            if drone_id in delivered:
                return False, (
                    f"Turn {turn_num}: drone {drone_id} already delivered"
                )

            actions.append((drone_id, target))

        # Apply actions
        for drone_id, target in actions:
            current = drone_pos[drone_id]

            if in_transit[drone_id]:
                # Drone is on a link; this turn it must arrive at dest zone
                expected_dest = transit_dest[drone_id]
                if target == current:
                    # Stayed on link (allowed if dest full)
                    continue
                if target != expected_dest:
                    return False, (
                        f"Turn {turn_num}: drone {drone_id}"
                        f"on link '{current}' "
                        f"must arrive at '{expected_dest}'"
                        f"but moved to '{target}'"
                    )
                # Arriving at expected_dest
                # Free link, enter zone
                link_use[current] = link_use.get(current, 0) + 1
                zone_arrivals[target] = zone_arrivals.get(target, 0) + 1
                drone_pos[drone_id] = target
                in_transit[drone_id] = False
                del transit_dest[drone_id]
                if target == graph.end_zone.name:
                    delivered.add(drone_id)
            else:
                # Drone is in a zone, performing a new action
                # Check if target is a zone (normal/priority move)
                # or a connection (starting restricted transit)
                if target in graph.zones:
                    # Zone move
                    nxt = graph.zones[target]
                    conn_zone: Optional[Connection] = graph.get_connection(
                        graph.zones[current], nxt
                    )
                    if conn_zone is None:
                        return False, (
                            f"Turn {turn_num}: no connection from "
                            f"'{current}' to '{target}'"
                        )
                    if nxt.zone_type == ZoneType.RESTRICTED:
                        return False, (
                            f"Turn {turn_num}: drone {drone_id} cannot enter "
                            f"restricted zone '{target}' in 1 turn"
                        )
                    if nxt.zone_type == ZoneType.BLOCKED:
                        return False, (
                            f"Turn {turn_num}: cannot"
                            f"enter blocked zone '{target}'"
                        )
                    zone_departures[current] = zone_departures.get(
                        current, 0) + 1
                    zone_arrivals[target] = zone_arrivals.get(target, 0) + 1
                    link_use[conn_zone.name] = link_use.get(
                        conn_zone.name, 0) + 1
                    drone_pos[drone_id] = target
                    if target == graph.end_zone.name:
                        delivered.add(drone_id)
                else:
                    # Must be a connection (starting restricted transit)
                    # Find connection by name (could be either direction)
                    conn_link: Optional[Connection] = None
                    for c in graph.connections:
                        if c.name == target or (
                            f"{c.zone_b.name}-{c.zone_a.name}" == target
                        ):
                            conn_link = c
                            break
                    if conn_link is None:
                        return False, (
                            f"Turn {turn_num}: target '{target}' is neither "
                            "a zone nor a connection"
                        )
                    # Determine destination side
                    if current == conn_link.zone_a.name:
                        dest_zone = conn_link.zone_b
                    elif current == conn_link.zone_b.name:
                        dest_zone = conn_link.zone_a
                    else:
                        return False, (
                            f"Turn {turn_num}: drone {drone_id} "
                            f"at '{current}' "
                            f"can't use connection '{target}'"
                        )
                    if dest_zone.zone_type != ZoneType.RESTRICTED:
                        return False, (
                            f"Turn {turn_num}: connection token used but "
                            f"destination '{dest_zone.name}' is not restricted"
                        )
                    zone_departures[current] = zone_departures.get(
                        current, 0) + 1
                    link_use[conn_link.name] = link_use.get(
                        conn_link.name, 0) + 1
                    drone_pos[drone_id] = conn_link.name
                    in_transit[drone_id] = True
                    transit_dest[drone_id] = dest_zone.name

        # Check capacity constraints at end of turn
        # Build current zone occupancy
        occ: Dict[str, int] = {z: 0 for z in graph.zones}
        for did, pos in drone_pos.items():
            if did in delivered:
                continue
            if not in_transit[did]:
                occ[pos] = occ.get(pos, 0) + 1

        for zname, count in occ.items():
            zone = graph.zones[zname]
            if zone.is_start or zone.is_end:
                continue
            if count > zone.max_drones:
                return False, (
                    f"Turn {turn_num}: zone '{zname}' has {count} drones "
                    f"(max={zone.max_drones})"
                )

        # Check link capacity (sum of drones on each link)
        link_occ: Dict[str, int] = {}
        for did, pos in drone_pos.items():
            if in_transit[did]:
                link_occ[pos] = link_occ.get(pos, 0) + 1
        for cname, count in link_occ.items():
            for c in graph.connections:
                if c.name == cname:
                    if count > c.max_link_capacity:
                        return False, (
                            f"Turn {turn_num}: link '{cname}' has {count} "
                            f"drones (max={c.max_link_capacity})"
                        )
                    break

    if len(delivered) != nb:
        return False, (
            f"Only {len(delivered)}/{nb} drones delivered"
        )

    return True, f"VALID: {nb} drones delivered in {len(turn_log)} turns"


if __name__ == "__main__":
    import sys
    from scheduler import Scheduler

    if len(sys.argv) < 2:
        print("Usage: python validator.py <map_file>")
        sys.exit(1)

    parser = MapParser()
    g = parser.parse_file(sys.argv[1])
    s = Scheduler(g, num_paths=6)
    log = s.run()
    ok, msg = validate(g, log)
    print(msg)
    sys.exit(0 if ok else 1)
