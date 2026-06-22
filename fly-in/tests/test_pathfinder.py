"""Tests for the pathfinder."""

from fly_in.parser.map_parser import MapParser
from fly_in.algorithm.pathfinder import PathFinder


def test_simple_linear_path() -> None:
    """Pathfinder returns the only path on a linear graph."""
    src = """
nb_drones: 1
start_hub: s 0 0
hub: m 1 0
end_hub: e 2 0
connection: s-m
connection: m-e
"""
    g = MapParser().parse_string(src)
    pf = PathFinder(g)
    assert g.start_zone is not None
    assert g.end_zone is not None
    path = pf.find_shortest_path(g.start_zone, g.end_zone)
    assert path is not None
    assert [z.name for z in path] == ["s", "m", "e"]


def test_path_cost_with_restricted_zone() -> None:
    """Restricted zones contribute 2 to path cost."""
    src = """
nb_drones: 1
start_hub: s 0 0
hub: r 1 0 [zone=restricted]
end_hub: e 2 0
connection: s-r
connection: r-e
"""
    g = MapParser().parse_string(src)
    pf = PathFinder(g)
    assert g.start_zone is not None
    assert g.end_zone is not None
    path = pf.find_shortest_path(g.start_zone, g.end_zone)
    assert path is not None
    # Cost: r=2, e=1 => total 3
    assert pf.path_true_cost(path) == 3


def test_k_best_paths_finds_alternatives() -> None:
    """k-best paths returns multiple distinct routes when available."""
    src = """
nb_drones: 1
start_hub: s 0 0
hub: a 1 1
hub: b 1 -1
end_hub: e 2 0
connection: s-a
connection: s-b
connection: a-e
connection: b-e
"""
    g = MapParser().parse_string(src)
    pf = PathFinder(g)
    assert g.start_zone is not None
    assert g.end_zone is not None
    paths = pf.find_k_best_paths(g.start_zone, g.end_zone, 2)
    assert len(paths) == 2
    sigs = {tuple(z.name for z in p) for p in paths}
    assert len(sigs) == 2


def test_bottleneck_capacity() -> None:
    """Bottleneck capacity reflects the smallest zone or link cap."""
    src = """
nb_drones: 1
start_hub: s 0 0
hub: m 1 0 [max_drones=3]
end_hub: e 2 0
connection: s-m [max_link_capacity=2]
connection: m-e
"""
    g = MapParser().parse_string(src)
    pf = PathFinder(g)
    assert g.start_zone is not None
    assert g.end_zone is not None
    path = pf.find_shortest_path(g.start_zone, g.end_zone)
    assert path is not None
    # min of m.max_drones=3, link s-m cap=2, link m-e cap=1 -> 1
    assert pf.bottleneck_capacity(path) == 1


def test_no_path_returns_none() -> None:
    """When no path exists, find_shortest_path returns None."""
    src = """
nb_drones: 1
start_hub: s 0 0
hub: isolated 5 5
end_hub: e 1 0
connection: s-e
"""
    g = MapParser().parse_string(src)
    pf = PathFinder(g)
    isolated = g.get_zone("isolated")
    assert isolated is not None
    assert g.end_zone is not None
    assert pf.find_shortest_path(isolated, g.end_zone) is None
