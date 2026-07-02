"""Tests for the maze adapter and level population.

The first two tests use a tiny *fake* generator so they run without the real
A-Maze-ing wheel installed.  The integration test exercises the real package
when it is available.
"""
from __future__ import annotations

from typing import List

import pytest

from src import maze_loader
from src.constants import PATH, WALL
from src.level import Level
from src.maze_loader import MazeData, load_maze


class _FakeGen:
    """Minimal stand-in exposing the same ``maze`` property as the real one."""

    def __init__(self, grid: List[List[int]]) -> None:
        self.maze = grid


def test_expand_shapes_and_walls(monkeypatch: pytest.MonkeyPatch) -> None:
    # A 2x2 edge-wall maze: open corridor across the top row, walls below.
    # bit: 1=N 2=E 4=S 8=W. Cell (0,0) open East+South, (1,0) open West.
    raw = [[6, 12], [3, 9]]

    def fake_ctor(**_kw: object) -> _FakeGen:
        return _FakeGen(raw)

    monkeypatch.setattr(maze_loader, "MazeGenerator", fake_ctor)
    data = load_maze(2, 2, seed=1)
    assert data.width == 2 * 2 + 1
    assert data.height == 2 * 2 + 1
    # Every cell centre is a path.
    for cy in range(2):
        for cx in range(2):
            assert data.grid[2 * cy + 1][2 * cx + 1] == PATH
    # The outer border is solid wall.
    assert data.grid[0][0] == WALL
    assert all(t in data.reachable for t in [data.player_start])


def test_missing_package_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(maze_loader, "MazeGenerator", None)
    with pytest.raises(maze_loader.MazeError):
        load_maze(10, 10, seed=1)


def _reachable_count(data: MazeData) -> int:
    return len(data.reachable)


@pytest.mark.integration
def test_real_generator_is_fully_clearable() -> None:
    pytest.importorskip("mazegenerator")
    data = load_maze(21, 21, seed=42)
    level = Level(data)
    # Every placed dot must sit on a tile reachable from the player.
    gums = level.pacgums | level.super_pacgums
    assert gums, "level should contain dots"
    assert gums <= data.reachable
    # All four corners are reachable, so all super-pacgums are collectible.
    assert level.super_pacgums <= data.reachable
    # Seed 42 is reproducible.
    again = load_maze(21, 21, seed=42)
    assert again.grid == data.grid
