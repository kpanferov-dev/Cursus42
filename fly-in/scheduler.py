"""Drone scheduling algorithm for optimal multi-drone routing.

Mechanics (spec-compliant):
- Each turn, every drone performs at most ONE action.
- Restricted zone transit takes 2 turns:
    Turn N  : drone leaves zone A, occupies link A-B.  Token: D-A-B
    Turn N+1: drone leaves link A-B, enters zone B.    Token: D-B
  While on the link the drone is NOT in any zone.
- Drones that just completed a transit move (arrived this turn) have already
  used their action and cannot move again in the same turn.
- Capacity rules:
    - A zone allows at most max_drones drones simultaneously
    (start/end unlimited).
    - A link allows at most max_link_capacity traversals simultaneously.
    - Drones leaving a zone free capacity IMMEDIATELY for the same turn.
    - Drones currently in transit toward a zone reserve a slot in that zone
      so other drones don't fill it before they arrive.
"""

from typing import Dict, List, Optional, Set, Tuple
from zone import Zone, ZoneType
from connection import Connection
from drone import Drone, DroneState
from graph import Graph
from pathfinder import PathFinder


class Scheduler:
    """Schedules and executes multi-drone routing through the network."""

    def __init__(
        self,
        graph: Graph,
        num_paths: int = 8,
        order_strategy: str = "farthest",
    ) -> None:
        """Initialize scheduler with the routing network.

        Args:
            graph: The drone network graph.
            num_paths: Number of diverse paths to compute.
            order_strategy: 'farthest' (drones close to goal first) or
                'nearest' (drones at start first).
        """
        self.graph: Graph = graph
        self.pathfinder: PathFinder = PathFinder(graph)
        self.num_paths: int = num_paths
        self.order_strategy: str = order_strategy
        self.drones: List[Drone] = []
        self.turn_log: List[List[str]] = []
        # Per-turn snapshot of zone occupancy (zone_name -> drone count)
        # Aligned with turn_log: occupancy_log[i] is the state AFTER turn i
        self.occupancy_log: List[Dict[str, int]] = []
        # transit: drone_id -> (connection, destination_zone)
        self._transit: Dict[int, Tuple[Connection, Zone]] = {}

    def run(self) -> List[List[str]]:
        """Execute the full simulation.

        Returns:
            Turn log: list of turns, each a list of output tokens.

        Raises:
            RuntimeError: If no path exists from start to end.
        """
        assert self.graph.start_zone is not None
        assert self.graph.end_zone is not None

        start = self.graph.start_zone
        nb = self.graph.nb_drones

        self.drones = [Drone(i + 1, start) for i in range(nb)]

        # zone_occ: zone_name -> set of drone_ids currently in that zone
        zone_occ: Dict[str, Set[int]] = {z: set() for z in self.graph.zones}
        for d in self.drones:
            zone_occ[start.name].add(d.drone_id)

        # Find diverse paths
        paths = self.pathfinder.find_k_best_paths(
            start, self.graph.end_zone, self.num_paths
        )
        if not paths:
            raise RuntimeError("No path found from start to end.")

        assignments = self._assign_paths(self.drones, paths)
        for d in self.drones:
            d.set_path(assignments[d.drone_id])

        self.turn_log = []
        self.occupancy_log = []
        self._transit = {}
        max_turns = 600

        for _ in range(max_turns):
            if all(d.is_delivered for d in self.drones):
                break
            tokens = self._turn(zone_occ)
            if tokens:
                self.turn_log.append(tokens)
                # Snapshot zone occupancy after this turn
                snapshot = {z: len(occ) for z, occ in zone_occ.items() if occ}
                self.occupancy_log.append(snapshot)
            else:
                # No progress — break to avoid infinite loop
                if not any(d.drone_id in self._transit for d in self.drones):
                    break

        return self.turn_log

    # ── Path assignment ────────────────────────────────────────────────────

    def _assign_paths(
        self,
        drones: List[Drone],
        paths: List[List[Zone]],
    ) -> Dict[int, List[Zone]]:
        """Assign each drone to a path using capacity-aware flow.

        For each drone, simulate adding it to each path and pick the path
        that minimises (cost + queue_delay), where queue_delay is the
        number of drones already queued / bottleneck capacity.

        Args:
            drones: Drones to assign.
            paths: Candidate paths.

        Returns:
            Mapping from drone_id to assigned path.
        """
        # Compute path properties once
        path_info: List[Tuple[int, int, List[Zone]]] = []
        for p in paths:
            cost = self.pathfinder.path_true_cost(p)
            cap = max(self.pathfinder.bottleneck_capacity(p), 1)
            path_info.append((cost, cap, p))

        # Sort by cost (we prefer cheaper paths)
        path_info.sort(key=lambda x: x[0])

        usage: List[int] = [0] * len(path_info)
        result: Dict[int, List[Zone]] = {}

        for d in drones:
            best_i, best_score = 0, 1e18
            for i, (cost, cap, _p) in enumerate(path_info):
                # Time to traverse for the (usage[i]+1)-th drone on this path
                # is approximately cost + ceil(usage[i] / cap)
                # We want to minimise total finish time
                queue_time = usage[i] / cap
                arrival_time = cost + queue_time
                if arrival_time < best_score:
                    best_score = arrival_time
                    best_i = i
            result[d.drone_id] = path_info[best_i][2]
            usage[best_i] += 1

        return result

    # ── Turn execution ─────────────────────────────────────────────────────

    def _turn(self, zone_occ: Dict[str, Set[int]]) -> List[str]:
        """Execute one simulation turn.

        Args:
            zone_occ: Current zone occupancy (mutated in place).

        Returns:
            Sorted list of output tokens for this turn.
        """
        tokens: List[str] = []
        acted: Set[int] = set()  # Drones that have acted this turn

        # Turn-local link usage counter
        link_used: Dict[str, int] = {}
        # Reservations: zones that will receive an arriving
        # transit drone NEXT turn
        # so that other drones don't take the spot
        reserved_in_zone: Dict[str, int] = {}

        # Pre-count current transit drones' destinations as reserved
        # (they will arrive THIS turn or next, so reserve NOW for
        # incoming starts)

        def zone_free(z: Zone) -> int:
            """Available capacity in z (considering reservations)."""
            if z.is_end or z.is_start:
                return 999999
            current = len(zone_occ[z.name])
            reserved = reserved_in_zone.get(z.name, 0)
            return z.max_drones - current - reserved

        def link_free(c: Connection) -> int:
            used = link_used.get(c.name, 0) + c.current_usage
            return c.max_link_capacity - used

        # ── Phase 1: complete restricted-zone arrivals (MANDATORY) ────────
        arriving = sorted(
            [d for d in self.drones
             if d.drone_id in self._transit and not d.is_delivered],
            key=lambda d: d.drone_id,
        )

        for drone in arriving:
            conn, dest = self._transit[drone.drone_id]
            # Use raw capacity (no reservations) since this drone IS the
            # reservation
            dest_current = len(zone_occ[dest.name])
            dest_cap = 999999 if (
                dest.is_end or dest.is_start) else dest.max_drones
            if dest_current < dest_cap:
                # Complete transit
                del self._transit[drone.drone_id]
                conn.current_usage = max(0, conn.current_usage - 1)

                zone_occ[dest.name].add(drone.drone_id)
                drone.current_zone = dest
                drone.advance_path()
                drone.state = DroneState.WAITING

                if dest.is_end:
                    drone.state = DroneState.DELIVERED

                tokens.append(f"{drone.name}-{dest.name}")
                acted.add(drone.drone_id)
            else:
                # Forced to stay on link; will retry next turn
                tokens.append(f"{drone.name}-{conn.name}")
                acted.add(drone.drone_id)

        # ── Phase 2: start new moves for waiting drones ───────────────────
        # Drones that completed transit this turn cannot move again
        # (they're already in `acted`)
        if self.order_strategy == "farthest":
            def sort_key(d: Drone) -> int:
                return -d.path_index
        else:
            def sort_key(d: Drone) -> int:
                return d.drone_id

        waiting = sorted(
            [d for d in self.drones
             if d.state == DroneState.WAITING
             and not d.is_delivered
             and d.drone_id not in self._transit
             and d.drone_id not in acted],
            key=sort_key,
        )

        for drone in waiting:
            nxt = drone.next_zone()
            if nxt is None:
                continue

            new_conn: Optional[Connection] = self.graph.get_connection(
                drone.current_zone, nxt
            )
            if new_conn is None:
                continue
            conn_to_use: Connection = new_conn

            if link_free(conn_to_use) <= 0:
                continue

            if zone_free(nxt) <= 0:
                continue

            # Depart current zone immediately (frees capacity for others)
            src = drone.current_zone.name
            zone_occ[src].discard(drone.drone_id)

            if nxt.zone_type == ZoneType.RESTRICTED:
                # Begin 2-turn transit
                link_used[conn_to_use.name] = (
                    link_used.get(conn_to_use.name, 0) + 1
                )
                conn_to_use.current_usage += 1
                # Reserve the destination so next turn's planning sees it
                reserved_in_zone[nxt.name] = (
                    reserved_in_zone.get(nxt.name, 0) + 1
                )
                drone.state = DroneState.IN_TRANSIT
                self._transit[drone.drone_id] = (conn_to_use, nxt)
                tokens.append(f"{drone.name}-{conn_to_use.name}")
            else:
                # Normal 1-turn move
                link_used[conn_to_use.name] = (
                    link_used.get(conn_to_use.name, 0) + 1
                )
                zone_occ[nxt.name].add(drone.drone_id)
                drone.current_zone = nxt
                drone.advance_path()

                if nxt.is_end:
                    drone.state = DroneState.DELIVERED

                tokens.append(f"{drone.name}-{nxt.name}")

        return tokens

    # ── Output helpers ─────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, float]:
        """Return simulation statistics.

        Returns:
            Dict containing total_turns, total_moves, avg_moves_per_turn.
            All values returned as floats for type consistency.
        """
        t = len(self.turn_log)
        m = sum(len(x) for x in self.turn_log)
        return {
            "total_turns": float(t),
            "total_moves": float(m),
            "avg_moves_per_turn": m / t if t > 0 else 0.0,
        }
