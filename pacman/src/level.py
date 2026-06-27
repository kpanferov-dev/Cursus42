"""The :class:`Level` ties a generated maze to its collectibles.

A level owns the wall grid, the set of pacgums (small dots filling the
corridors), the four super-pacgums (placed in the corners) and the spawn
points for the player and the ghosts.
"""
from __future__ import annotations

from typing import List, Set, Tuple

from .constants import PATH
from .maze_loader import MazeData

Tile = Tuple[int, int]


class Level:
    """A single playable level built from a :class:`MazeData`."""

    def __init__(self, maze: MazeData) -> None:
        """Create the level, scattering pacgums over the corridors."""
        self.grid: List[List[int]] = maze.grid
        self.width: int = maze.width
        self.height: int = maze.height
        self.player_start: Tile = maze.player_start
        self.ghost_starts: List[Tile] = maze.ghost_starts
        self.pacgums: Set[Tile] = set()
        self.super_pacgums: Set[Tile] = set()
        self._populate(maze)

    def _populate(self, maze: MazeData) -> None:
        """Place pacgums on most corridor tiles and super-pacgums in corners.

        The player spawn tile is intentionally left empty.
        """
        reserved: Set[Tile] = {self.player_start}
        reserved.update(maze.ghost_starts)
        for tile in maze.corners:
            self.super_pacgums.add(tile)
            reserved.add(tile)
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] != PATH:
                    continue
                if (x, y) in reserved:
                    continue
                self.pacgums.add((x, y))

    @property
    def total_gums(self) -> int:
        """Total number of edible dots remaining (pacgums + super)."""
        return len(self.pacgums) + len(self.super_pacgums)

    def eat(self, tile: Tile) -> str:
        """Consume a dot at *tile*.

        Returns:
            ``"pacgum"``, ``"super"`` or ``"none"`` depending on what was
            present at that tile.
        """
        if tile in self.pacgums:
            self.pacgums.discard(tile)
            return "pacgum"
        if tile in self.super_pacgums:
            self.super_pacgums.discard(tile)
            return "super"
        return "none"

    @property
    def cleared(self) -> bool:
        """True once every dot of the level has been eaten."""
        return self.total_gums == 0
