"""Adapter around the external *A-Maze-ing* (``mazegenerator``) package.

The package is used **as-is**.  Its real constructor signature (read from the
source, *not* from the misleading README quick-start) is::

    MazeGenerator(size=(w, h), perfect=False, entry_cell=(0, 0),
                  exit_cell=(-1, -1), seed=0)

It exposes a ``maze`` 2D list where every cell stores its four walls in the
low bits (1=North, 2=East, 4=South, 8=West) and a value of ``15`` marks a
solid block (it draws a "42" in the middle).  We expand this "edge wall"
grid into a classic Pac-Man "fat wall" grid of size ``(2w+1) x (2h+1)``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .constants import PATH, WALL

# Imported lazily-safely so a missing dependency is reported, not crashed.
try:
    from mazegenerator import MazeGenerator
except Exception as _err:  # pragma: no cover - exercised at runtime only
    MazeGenerator = None
    _IMPORT_ERROR: Optional[Exception] = _err
else:
    _IMPORT_ERROR = None

Tile = Tuple[int, int]
SOLID_BLOCK = 15


class MazeError(Exception):
    """Raised when the external generator cannot produce a usable maze."""


@dataclass
class MazeData:
    """A ready-to-play maze expanded into a tile grid.

    Attributes:
        grid: ``grid[y][x]`` is ``WALL`` or ``PATH``.
        width: Number of tile columns.
        height: Number of tile rows.
        player_start: Tile where the player spawns (centre of the maze).
        ghost_starts: Four corner tiles where ghosts spawn.
        corners: Four corner tiles where super-pacgums are placed.
    """

    grid: List[List[int]]
    width: int
    height: int
    player_start: Tile
    ghost_starts: List[Tile] = field(default_factory=list)
    corners: List[Tile] = field(default_factory=list)


def _expand(raw: List[List[int]], cell_w: int, cell_h: int) -> List[List[int]]:
    """Expand the edge-wall maze into a fat-wall tile grid."""
    gw, gh = 2 * cell_w + 1, 2 * cell_h + 1
    grid = [[WALL] * gw for _ in range(gh)]
    for cy in range(cell_h):
        for cx in range(cell_w):
            cell = raw[cy][cx]
            if cell == SOLID_BLOCK:
                continue
            grid[2 * cy + 1][2 * cx + 1] = PATH
            if not cell & 1:                       # open North
                grid[2 * cy][2 * cx + 1] = PATH
            if not cell & 2:                       # open East
                grid[2 * cy + 1][2 * cx + 2] = PATH
            if not cell & 4:                       # open South
                grid[2 * cy + 2][2 * cx + 1] = PATH
            if not cell & 8:                       # open West
                grid[2 * cy + 1][2 * cx] = PATH
    return grid


def _nearest_path(grid: List[List[int]], target: Tile) -> Tile:
    """Breadth-first search for the closest ``PATH`` tile to *target*."""
    gh, gw = len(grid), len(grid[0])
    tx, ty = target
    tx = max(0, min(gw - 1, tx))
    ty = max(0, min(gh - 1, ty))
    best: Optional[Tile] = None
    best_dist = 10 ** 9
    for y in range(gh):
        for x in range(gw):
            if grid[y][x] != PATH:
                continue
            dist = (x - tx) ** 2 + (y - ty) ** 2
            if dist < best_dist:
                best_dist, best = dist, (x, y)
    if best is None:
        raise MazeError("generated maze has no walkable tile")
    return best


def load_maze(width: int, height: int, seed: int) -> MazeData:
    """Generate a maze and adapt it to a playable :class:`MazeData`.

    Args:
        width: Maze width in cells (before expansion).
        height: Maze height in cells (before expansion).
        seed: Seed for reproducibility (use ``0`` for a random maze).

    Raises:
        MazeError: If the external package is missing or generation fails.
    """
    if MazeGenerator is None:
        raise MazeError(
            f"the 'mazegenerator' package is not installed: {_IMPORT_ERROR}")
    try:
        generator = MazeGenerator(size=(width, height), perfect=False,
                                  seed=seed)
        raw = generator.maze
    except Exception as error:  # adapt to *their* failures, never crash
        raise MazeError(f"maze generation failed: {error}") from error

    if not raw or not raw[0]:
        raise MazeError("the generator returned an empty maze")

    grid = _expand(raw, width, height)
    gw, gh = len(grid[0]), len(grid)

    player_start = _nearest_path(grid, (gw // 2, gh // 2))
    corner_targets: List[Tile] = [
        (1, 1), (gw - 2, 1), (1, gh - 2), (gw - 2, gh - 2)]
    corners = [_nearest_path(grid, c) for c in corner_targets]
    return MazeData(grid=grid, width=gw, height=gh,
                    player_start=player_start, ghost_starts=list(corners),
                    corners=corners)
