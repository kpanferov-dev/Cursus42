"""Shared constants, tile codes and enumerations for the Pac-Man game."""
from __future__ import annotations

from enum import Enum, auto

# --- Tile codes used by the expanded game grid ------------------------------
# The A-Maze-ing package uses an "edge wall" encoding (walls live on the
# borders between cells).  We convert that into a classic Pac-Man "fat wall"
# grid where each tile is either a wall or a walkable corridor.
WALL: int = 1
PATH: int = 0

# --- Rendering -------------------------------------------------------------
TILE_SIZE: int = 24          # pixel size of one grid tile
HUD_HEIGHT: int = 40         # pixel height of the bottom status bar
FPS: int = 60

# Colors (R, G, B)
COLOR_BG = (0, 0, 0)
COLOR_WALL = (33, 33, 222)
COLOR_PATH = (0, 0, 0)
COLOR_PACGUM = (255, 255, 180)
COLOR_SUPER = (255, 184, 174)
COLOR_PLAYER = (255, 224, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_TITLE = (255, 224, 0)
COLOR_FRIGHT = (40, 40, 255)       # ghost color while edible
COLOR_EATEN = (120, 120, 120)      # ghost "eyes" color after being eaten

# One distinct color per ghost (Blinky, Pinky, Inky, Clyde).
GHOST_COLORS = [
    (255, 0, 0),       # red    - Blinky
    (255, 184, 222),   # pink   - Pinky
    (0, 255, 222),     # cyan   - Inky
    (255, 184, 71),    # orange - Clyde
]


class Direction(Enum):
    """The four movement directions plus a neutral "stopped" state."""

    NONE = (0, 0)
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        """Horizontal component of the direction."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Vertical component of the direction."""
        return self.value[1]


class GameState(Enum):
    """High level states of the application state machine."""

    MENU = auto()
    PLAYING = auto()
    PAUSED = auto()
    GAME_OVER = auto()
    VICTORY = auto()
    ENTER_NAME = auto()
