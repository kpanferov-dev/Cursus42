"""Pathfinding and flow algorithms for the Fly-in project.

Everything here is implemented from scratch (no graph libraries). Two
complementary techniques are provided:

* :meth:`PathFinder.shortest_path` runs Dijkstra over the turn cost of
  entering each zone, gently preferring ``priority`` zones. It is handy
  for diagnostics and single-drone routing.
* :meth:`PathFinder.find_lanes` builds a set of capacity-respecting
  routes ("lanes") by computing a maximum flow on a node-split graph and
  decomposing that flow into paths. These lanes feed the scheduler.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from models import Network


class NoRouteError(Exception):
    """Raised when no valid route exists between start and end."""


@dataclass
class Lane:
    """A single start-to-end route together with derived metrics.

    Attributes:
        zones: Ordered zone names from start to end (inclusive).
        cost: Total turn cost of one drone traversing the lane alone.
    """

    zones: List[str]
    cost: int

    @property
    def hops(self) -> int:
        """Return the number of moves (edges) along the lane."""
        return len(self.zones) - 1


class _MaxFlow:
    """A small Edmonds-Karp maximum-flow solver on integer capacities."""

    def __init__(self, node_count: int) -> None:
        self._capacity: List[Dict[int, int]] = [
            {} for _ in range(node_count)]
        self._initial: List[Dict[int, int]] = [
            {} for _ in range(node_count)]

    def add_edge(self, src: int, dst: int, capacity: int) -> None:
        """Add a directed edge and its zero-capacity reverse arc."""
        self._capacity[src][dst] = self._capacity[src].get(dst, 0) + capacity
        self._capacity[dst].setdefault(src, 0)
        self._initial[src][dst] = self._initial[src].get(dst, 0) + capacity

    def _bfs(self, source: int, sink: int) -> Optional[Dict[int, int]]:
        """Return a parent map describing one shortest augmenting path."""
        parents: Dict[int, int] = {source: source}
        queue: List[int] = [source]
        while queue:
            node = queue.pop(0)
            if node == sink:
                return parents
            for nxt, residual in self._capacity[node].items():
                if residual > 0 and nxt not in parents:
                    parents[nxt] = node
                    queue.append(nxt)
        return None

    def solve(self, source: int, sink: int) -> int:
        """Compute the maximum flow from ``source`` to ``sink``."""
        flow = 0
        while True:
            parents = self._bfs(source, sink)
            if parents is None:
                break
            node = sink
            while node != source:
                previous = parents[node]
                self._capacity[previous][node] -= 1
                self._capacity[node][previous] += 1
                node = previous
            flow += 1
        return flow

    def forward_flow(self, src: int, dst: int) -> int:
        """Return the flow currently sent along the original arc."""
        initial = self._initial[src].get(dst, 0)
        if initial == 0:
            return 0
        return initial - self._capacity[src].get(dst, 0)

    def consume_unit(self, src: int, dst: int) -> None:
        """Remove one unit of flow from an arc during decomposition."""
        self._capacity[src][dst] += 1


@dataclass
class PathFinder:
    """Compute routes through a :class:`~models.Network`.

    Attributes:
        network: The network to operate on.
    """

    network: Network
    _index: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._index = {name: i for i, name in enumerate(self.network.zones)}

    def shortest_path(self) -> Optional[Lane]:
        """Return the cheapest start-to-end route by turn cost.

        Priority zones are mildly preferred: among equally costly routes,
        the one passing through more priority zones wins.

        Returns:
            A :class:`Lane`, or ``None`` if the end is unreachable.
        """
        start = self.network.start.name
        end = self.network.end.name
        best_cost: Dict[str, Tuple[int, int]] = {start: (0, 0)}
        previous: Dict[str, str] = {}
        heap: List[Tuple[int, int, str]] = [(0, 0, start)]
        while heap:
            cost, priority_penalty, name = heapq.heappop(heap)
            if (cost, priority_penalty) > best_cost.get(
                    name, (cost, priority_penalty)):
                continue
            if name == end:
                return self._build_lane(previous, start, end)
            for neighbour in self.network.neighbours(name):
                zone = self.network.zones[neighbour]
                if not zone.zone_type.is_traversable:
                    continue
                new_cost = cost + zone.enter_cost
                new_penalty = priority_penalty
                if not zone.zone_type.is_priority:
                    new_penalty += 1
                candidate = (new_cost, new_penalty)
                if candidate < best_cost.get(neighbour, (candidate[0] + 1, 0)):
                    best_cost[neighbour] = candidate
                    previous[neighbour] = name
                    heapq.heappush(heap, (new_cost, new_penalty, neighbour))
        return None

    def _build_lane(
        self, previous: Dict[str, str], start: str, end: str
    ) -> Lane:
        """Reconstruct a :class:`Lane` from a predecessor map."""
        zones: List[str] = [end]
        while zones[-1] != start:
            zones.append(previous[zones[-1]])
        zones.reverse()
        return Lane(zones=zones, cost=self._lane_cost(zones))

    def _lane_cost(self, zones: List[str]) -> int:
        """Return the total turn cost of traversing a zone sequence."""
        return sum(self.network.zones[name].enter_cost
                   for name in zones[1:])

    def find_lanes(self) -> List[Lane]:
        """Return capacity-respecting lanes via max-flow decomposition.

        Returns:
            A list of :class:`Lane` routes whose simultaneous use never
            exceeds any zone or connection capacity.

        Raises:
            NoRouteError: If the end zone cannot be reached at all.
        """
        if self.shortest_path() is None:
            raise NoRouteError("no route exists from start to end")
        cap = max(self.network.nb_drones, 1)
        node_count = 2 * len(self.network.zones)
        flow = _MaxFlow(node_count)
        self._build_flow_graph(flow, cap)
        source = self._in_node(self.network.start.name)
        sink = self._out_node(self.network.end.name)
        flow.solve(source, sink)
        lanes = self._decompose(flow, source, sink)
        if not lanes:
            raise NoRouteError("no route exists from start to end")
        lanes.sort(key=lambda lane: (lane.cost, lane.hops))
        return lanes

    def _build_flow_graph(self, flow: _MaxFlow, cap: int) -> None:
        """Populate the node-split flow graph with capacities."""
        for name, zone in self.network.zones.items():
            in_node = self._in_node(name)
            out_node = self._out_node(name)
            if zone.is_unlimited:
                node_cap = cap
            else:
                node_cap = min(zone.capacity, cap)
            if not zone.zone_type.is_traversable:
                node_cap = 0
            flow.add_edge(in_node, out_node, node_cap)
        for connection in self.network.connections.values():
            link_cap = min(connection.capacity, cap)
            first_out = self._out_node(connection.first)
            second_in = self._in_node(connection.second)
            second_out = self._out_node(connection.second)
            first_in = self._in_node(connection.first)
            flow.add_edge(first_out, second_in, link_cap)
            flow.add_edge(second_out, first_in, link_cap)

    def _decompose(
        self, flow: _MaxFlow, source: int, sink: int
    ) -> List[Lane]:
        """Decompose a computed flow into individual unit-flow lanes."""
        names = list(self.network.zones)
        lanes: List[Lane] = []
        while True:
            path_nodes = self._extract_unit_path(flow, source, sink)
            if path_nodes is None:
                break
            zones = self._nodes_to_zones(path_nodes, names)
            lanes.append(Lane(zones=zones, cost=self._lane_cost(zones)))
        return lanes

    def _extract_unit_path(
        self, flow: _MaxFlow, source: int, sink: int
    ) -> Optional[List[int]]:
        """Walk one unit of remaining flow from source to sink."""
        path: List[int] = [source]
        node = source
        while node != sink:
            advanced = False
            for nxt in range(len(self.network.zones) * 2):
                if flow.forward_flow(node, nxt) > 0:
                    flow.consume_unit(node, nxt)
                    path.append(nxt)
                    node = nxt
                    advanced = True
                    break
            if not advanced:
                return None
        return path

    def _nodes_to_zones(
        self, path_nodes: List[int], names: List[str]
    ) -> List[str]:
        """Collapse split in/out node ids back into zone names."""
        zones: List[str] = []
        for node in path_nodes:
            if node % 2 == 0:
                zones.append(names[node // 2])
        return zones

    def _in_node(self, name: str) -> int:
        """Return the split-graph 'in' node id of a zone."""
        return 2 * self._index[name]

    def _out_node(self, name: str) -> int:
        """Return the split-graph 'out' node id of a zone."""
        return 2 * self._index[name] + 1
