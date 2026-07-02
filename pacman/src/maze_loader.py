"""Adapter around the external *A-Maze-ing* (``mazegenerator``) package.

The package is used **as-is** (V.4): we adapt to *their* interface, never the
other way round.  Its real constructor signature (verified against the
installed wheel, ``mazegenerator`` 2.0.2) is::

    MazeGenerator(size=(w, h), perfect=False, entry_cell=(0, 0),
                  exit_cell=(-1, -1), seed=0)

It exposes a ``maze`` 2D list where every cell stores its four walls in the
low bits (1=North, 2=East, 4=South, 8=West) and a value of ``15`` marks a
solid block (the package draws a "42" in the middle of the maze).  We expand
this "edge wall" grid into a classic Pac-Man "fat wall" grid of size
``(2w+1) x (2h+1)``.

The subject also mandates ``PERFECT = False`` so the corridors loop, which is
what makes the layout Pac-Man-compatible.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

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
Grid = List[List[int]]
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
        reachable: Every PATH tile reachable from ``player_start``.  Used by
            :class:`~src.level.Level` so dots are only placed where the player
            can actually collect them (guaranteeing a clearable level).
    """

    grid: Grid
    width: int
    height: int
    player_start: Tile
    ghost_starts: List[Tile] = field(default_factory=list)
    corners: List[Tile] = field(default_factory=list)
    reachable: Set[Tile] = field(default_factory=set)


def _expand(raw: Grid, cell_w: int, cell_h: int) -> Grid:
    """Expand the edge-wall maze into a fat-wall tile grid."""
    gw, gh = 2 * cell_w + 1, 2 * cell_h + 1
    grid: Grid = [[WALL] * gw for _ in range(gh)]
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


def _flood(grid: Grid, start: Tile) -> Set[Tile]:
    """Return every PATH tile reachable from *start* (4-connectivity)."""
    gh, gw = len(grid), len(grid[0])
    seen: Set[Tile] = {start}
    queue: deque[Tile] = deque([start])
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < gw and 0 <= ny < gh \
                    and grid[ny][nx] == PATH and (nx, ny) not in seen:
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def _all_path_tiles(grid: Grid) -> List[Tile]:
    """List every walkable tile in the grid."""
    return [(x, y)
            for y, row in enumerate(grid)
            for x, cell in enumerate(row) if cell == PATH]


def _nearest(candidates: List[Tile], target: Tile) -> Tile:
    """Return the candidate tile closest (squared distance) to *target*."""
    tx, ty = target
    return min(
        candidates,
        key=lambda t: (t[0] - tx) ** 2 + (t[1] - ty) ** 2,
    )


def load_maze(width: int, height: int, seed: int) -> MazeData:
    """Generate a maze and adapt it to a playable :class:`MazeData`.

    Args:
        width: Maze width in cells (before expansion).
        height: Maze height in cells (before expansion).
        seed: Seed for reproducibility (use ``0`` for a random maze, as the
            package interprets a non-positive seed as "fully random").

    Returns:
        A :class:`MazeData` whose ``player_start`` and four ``corners`` all lie
        in a single connected component, so the level is always clearable.

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

    walkable = _all_path_tiles(grid)
    if not walkable:
        raise MazeError("generated maze has no walkable tile")

    # The player spawns near the centre; everything must be reachable from
    # there, so we work inside that single connected component.
    centre_tile = _nearest(walkable, (gw // 2, gh // 2))
    reachable = _flood(grid, centre_tile)
    component = sorted(reachable)

    player_start = _nearest(component, (gw // 2, gh // 2))
    corner_targets: List[Tile] = [
        (1, 1), (gw - 2, 1), (1, gh - 2), (gw - 2, gh - 2)]
    corners = [_nearest(component, c) for c in corner_targets]
    return MazeData(grid=grid, width=gw, height=gh,
                    player_start=player_start, ghost_starts=list(corners),
                    corners=corners, reachable=reachable)
