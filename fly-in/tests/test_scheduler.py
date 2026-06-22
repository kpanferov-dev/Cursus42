"""Integration tests for the scheduler and validator."""

import os
from fly_in.parser.map_parser import MapParser
from fly_in.algorithm.scheduler import Scheduler
from fly_in.simulation.validator import validate

MAPS_DIR = os.path.join(os.path.dirname(__file__), "..", "maps")


def _run_and_validate(map_file: str, num_paths: int = 6) -> int:
    """Run a map and validate the output. Returns turn count."""
    parser = MapParser()
    g = parser.parse_file(map_file)
    s = Scheduler(g, num_paths=num_paths)
    log = s.run()
    ok, msg = validate(g, log)
    assert ok, f"Validation failed for {map_file}: {msg}"
    return len(log)


def test_linear_path_meets_target() -> None:
    """Easy: linear path with 2 drones, target ≤6."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "01_linear_path.txt"))
    assert turns <= 6


def test_simple_fork_meets_target() -> None:
    """Easy: simple fork with 3 drones, target ≤6."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "02_simple_fork.txt"))
    assert turns <= 6


def test_basic_capacity_meets_target() -> None:
    """Easy: basic capacity with 4 drones, target ≤8."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "03_basic_capacity.txt"))
    assert turns <= 8


def test_dead_end_trap_meets_target() -> None:
    """Medium: dead-end trap with 5 drones, target ≤15."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "01_dead_end_trap.txt"))
    assert turns <= 15


def test_circular_loop_meets_target() -> None:
    """Medium: circular loop with 6 drones, target ≤20."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "02_circular_loop.txt"))
    assert turns <= 20


def test_priority_puzzle_meets_target() -> None:
    """Medium: priority puzzle with 4 drones, target ≤12."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "03_priority_puzzle.txt"))
    assert turns <= 12


def test_maze_nightmare_meets_target() -> None:
    """Hard: maze nightmare with 8 drones, target ≤45."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "01_maze_nightmare.txt"))
    assert turns <= 45


def test_capacity_hell_meets_target() -> None:
    """Hard: capacity hell with 12 drones, target ≤60."""
    turns = _run_and_validate(os.path.join(MAPS_DIR, "02_capacity_hell.txt"))
    assert turns <= 60


def test_ultimate_challenge_meets_target() -> None:
    """Hard: ultimate challenge with 15 drones, target ≤35."""
    turns = _run_and_validate(
        os.path.join(MAPS_DIR, "03_ultimate_challenge.txt")
    )
    assert turns <= 35


def test_impossible_dream_matches_record() -> None:
    """Challenger: impossible dream with 25 drones, record=45."""
    turns = _run_and_validate(
        os.path.join(MAPS_DIR, "01_the_impossible_dream.txt")
    )
    assert turns <= 45


def test_all_drones_delivered() -> None:
    """Every map run must deliver all drones."""
    parser = MapParser()
    for fname in os.listdir(MAPS_DIR):
        if not fname.endswith(".txt"):
            continue
        g = parser.parse_file(os.path.join(MAPS_DIR, fname))
        s = Scheduler(g, num_paths=6)
        log = s.run()
        ok, msg = validate(g, log)
        assert ok, f"{fname}: {msg}"
