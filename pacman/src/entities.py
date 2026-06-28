"""Moving entities: the :class:`Player` and the :class:`Ghost`.

Entities are *tile locked*: they always travel from the centre of one tile to
the centre of an adjacent tile.  A ``progress`` value in ``[0, 1]`` is used to
interpolate the pixel position for smooth rendering, while all game logic
(collisions, eating, AI decisions) happens on integer tile coordinates.
"""
from __future__ import annotations

import random
from collections import deque
from typing import List, Optional, Tuple

from .constants import PATH, Direction

Tile = Tuple[int, int]
Grid = List[List[int]]


class MovingEntity:
    """Base class implementing tile-locked smooth movement."""

    def __init__(self, tile: Tile, speed: float) -> None:
        """Initialise at *tile* with a given *speed* (tiles per frame)."""
        self.tile: Tile = tile
        self.target: Tile = tile
        self.progress: float = 0.0
        self.speed: float = speed
        self.direction: Direction = Direction.NONE

    @property
    def aligned(self) -> bool:
        """True when the entity sits exactly on a tile centre."""
        return self.progress == 0.0 and self.tile == self.target

    @property
    def pixel_pos(self) -> Tuple[float, float]:
        """Interpolated tile-space position (still in tile units)."""
        sx, sy = self.tile
        tx, ty = self.target
        return (sx + (tx - sx) * self.progress,
                sy + (ty - sy) * self.progress)

    def _can_move(self, grid: Grid, tile: Tile) -> bool:
        x, y = tile
        if not (0 <= y < len(grid) and 0 <= x < len(grid[0])):
            return False
        return grid[y][x] == PATH

    def _advance(self, grid: Grid) -> bool:
        """Advance toward the current target. Returns True when a tile is
        reached (i.e. the entity becomes aligned this frame)."""
        if self.tile == self.target:
            return True
        self.progress += self.speed
        if self.progress >= 1.0:
            self.tile = self.target
            self.progress = 0.0
            return True
        return False

    def _start_move(self, grid: Grid, direction: Direction) -> bool:
        """Try to begin moving one tile in *direction*."""
        nx, ny = self.tile[0] + direction.dx, self.tile[1] + direction.dy
        if self._can_move(grid, (nx, ny)):
            self.target = (nx, ny)
            self.direction = direction
            self.progress = 0.0
            return True
        return False


class Player(MovingEntity):
    """The player character, driven by buffered keyboard input."""

    def __init__(self, tile: Tile, speed: float = 0.12) -> None:
        """Create the player at *tile*."""
        super().__init__(tile, speed)
        self.wanted: Direction = Direction.NONE

    def request(self, direction: Direction) -> None:
        """Buffer a direction; applied as soon as the path allows it."""
        self.wanted = direction

    def update(self, grid: Grid) -> None:
        """Advance the player for one frame."""
        reached = self._advance(grid)
        if not reached:
            return
        if self.wanted is not Direction.NONE and \
                self._start_move(grid, self.wanted):
            return
        if self.direction is not Direction.NONE:
            self._start_move(grid, self.direction)

    def reset(self, tile: Tile) -> None:
        """Place the player back at *tile* and clear movement."""
        self.tile = self.target = tile
        self.progress = 0.0
        self.direction = self.wanted = Direction.NONE


class Ghost(MovingEntity):
    """An autonomous ghost: chases, flees when frightened, returns home."""

    def __init__(self, tile: Tile, color_index: int,
                 speed: float = 0.09) -> None:
        """Create a ghost at *tile* belonging to *color_index* (0-3)."""
        super().__init__(tile, speed)
        self.home: Tile = tile
        self.color_index = color_index
        self.frightened: bool = False
        self.eaten: bool = False
        self.hidden: bool = False
        self.respawn_time: float = 0.0

    def set_frightened(self, value: bool) -> None:
        """Toggle the frightened (edible) state, unless currently eaten."""
        if not self.eaten:
            self.frightened = value

    def get_eaten(self) -> None:
        """Mark the ghost as eaten; it heads back to its home corner."""
        self.eaten = True
        self.frightened = False
        self.hidden = True

    def reset(self) -> None:
        """Send the ghost back to its home corner, alive and hostile."""
        self.tile = self.target = self.home
        self.progress = 0.0
        self.direction = Direction.NONE
        self.frightened = False
        self.eaten = False

    def update(self, grid: Grid, player_tile: Tile, frozen: bool) -> None:
        """Advance the ghost for one frame toward its current goal."""
        if frozen:
            return
        reached = self._advance(grid)
        if not reached:
            return
        if self.eaten and self.tile == self.home:
            self.eaten = False
        goal = self.home if self.eaten else player_tile
        self._choose_next(grid, goal)

    def _choose_next(self, grid: Grid, goal: Tile) -> None:
        """Pick the next tile to move into, given the current goal."""
        options = self._neighbors(grid)
        if not options:
            self.direction = Direction.NONE
            return
        # Avoid reversing unless it is the only option (classic behaviour).
        reverse = (-self.direction.dx, -self.direction.dy)
        forward = [o for o in options
                   if (o[1].dx, o[1].dy) != reverse] or options
        if self.frightened and not self.eaten:
            choice = max(forward, key=lambda o: self._dist(o[0], goal))
            if random.random() < 0.35:        # add some unpredictability
                choice = random.choice(forward)
        else:
            choice = min(forward, key=lambda o: self._dist(o[0], goal))
        target, direction = choice
        self.target, self.direction, self.progress = target, direction, 0.0

    def _neighbors(self, grid: Grid) -> List[Tuple[Tile, Direction]]:
        result: List[Tuple[Tile, Direction]] = []
        for direction in (Direction.UP, Direction.DOWN,
                          Direction.LEFT, Direction.RIGHT):
            nx, ny = self.tile[0] + direction.dx, self.tile[1] + direction.dy
            if self._can_move(grid, (nx, ny)):
                result.append(((nx, ny), direction))
        return result

    @staticmethod
    def _dist(a: Tile, b: Tile) -> int:
        return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def bfs_path(grid: Grid, start: Tile, goal: Tile) -> Optional[List[Tile]]:
    """Shortest tile path from *start* to *goal* (utility, optional use)."""
    if start == goal:
        return [start]
    gh, gw = len(grid), len(grid[0])
    queue: deque[Tile] = deque([start])
    came: dict[Tile, Tile] = {start: start}
    while queue:
        cx, cy = queue.popleft()
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < gw and 0 <= ny < gh):
                continue
            if grid[ny][nx] != PATH or (nx, ny) in came:
                continue
            came[(nx, ny)] = (cx, cy)
            if (nx, ny) == goal:
                path = [goal]
                while path[-1] != start:
                    path.append(came[path[-1]])
                return path[::-1]
            queue.append((nx, ny))
    return None
