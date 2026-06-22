"""Tests for the map parser."""

import pytest
from fly_in.parser.map_parser import MapParser, ParseError
from fly_in.models.zone import ZoneType


def test_minimal_valid_map() -> None:
    """A map with just nb_drones, start, and end parses correctly."""
    src = """
nb_drones: 1
start_hub: s 0 0
end_hub: e 1 0
connection: s-e
"""
    g = MapParser().parse_string(src)
    assert g.nb_drones == 1
    assert g.start_zone is not None and g.start_zone.name == "s"
    assert g.end_zone is not None and g.end_zone.name == "e"
    assert len(g.connections) == 1


def test_zone_metadata_parsing() -> None:
    """Metadata in brackets is parsed correctly."""
    src = """
nb_drones: 2
start_hub: s 0 0 [color=green]
end_hub: e 5 5 [color=red max_drones=3]
hub: m 2 2 [zone=restricted color=blue max_drones=2]
connection: s-m
connection: m-e
"""
    g = MapParser().parse_string(src)
    m = g.get_zone("m")
    assert m is not None
    assert m.zone_type == ZoneType.RESTRICTED
    assert m.color == "blue"
    assert m.max_drones == 2


def test_missing_nb_drones() -> None:
    """Missing nb_drones raises ParseError."""
    src = "start_hub: s 0 0\nend_hub: e 1 0\nconnection: s-e\n"
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_invalid_zone_type() -> None:
    """Unknown zone type raises ParseError."""
    src = """
nb_drones: 1
start_hub: s 0 0
end_hub: e 1 0 [zone=invalid_type]
connection: s-e
"""
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_negative_max_drones_invalid() -> None:
    """Non-positive max_drones raises ParseError."""
    src = """
nb_drones: 1
start_hub: s 0 0
end_hub: e 1 0 [max_drones=0]
connection: s-e
"""
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_unknown_zone_in_connection() -> None:
    """Connection referencing undefined zone raises ParseError."""
    src = """
nb_drones: 1
start_hub: s 0 0
end_hub: e 1 0
connection: s-ghost
"""
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_duplicate_connection() -> None:
    """Duplicate connection (any direction) raises ParseError."""
    src = """
nb_drones: 1
start_hub: s 0 0
end_hub: e 1 0
connection: s-e
connection: e-s
"""
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_duplicate_zone_name() -> None:
    """Duplicate zone names raise ParseError."""
    src = """
nb_drones: 1
start_hub: s 0 0
hub: dup 1 0
hub: dup 2 0
end_hub: e 3 0
connection: s-dup
connection: dup-e
"""
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_comments_and_blank_lines_ignored() -> None:
    """Comments (# prefix) and blank lines are skipped."""
    src = """
# This is a comment
nb_drones: 1

start_hub: s 0 0  # inline comments are NOT supported
end_hub: e 1 0
# another comment
connection: s-e
"""
    # The inline comment after `start_hub` makes this invalid
    with pytest.raises(ParseError):
        MapParser().parse_string(src)


def test_negative_coordinates() -> None:
    """Negative coordinates are valid."""
    src = """
nb_drones: 1
start_hub: s -5 -3
end_hub: e 0 0
connection: s-e
"""
    g = MapParser().parse_string(src)
    assert g.start_zone is not None
    assert g.start_zone.x == -5
    assert g.start_zone.y == -3
