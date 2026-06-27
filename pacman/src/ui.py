"""All pygame drawing code lives here, isolated from the game logic.

The :class:`Renderer` knows how to draw every screen (menu, gameplay, pause
overlay, game-over and victory) given the current :class:`~src.game.Game`
state.  Keeping rendering separate keeps the rest of the code testable
without a display.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Iterable, List, Tuple

import pygame

from . import constants as C
from .constants import GameState

if TYPE_CHECKING:                       # avoid an import cycle at runtime
    from .entities import Ghost, Player
    from .game import Game

Tile = Tuple[int, int]


class Renderer:
    """Draws the game; owns the pygame window and fonts."""

    def __init__(self, cols: int, rows: int) -> None:
        """Create a window large enough for a *cols* x *rows* tile grid."""
        width = cols * C.TILE_SIZE
        height = rows * C.TILE_SIZE + C.HUD_HEIGHT
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Pac-Man - Ghosts! More ghosts!")
        self.font = pygame.font.SysFont("consolas", 18)
        self.big = pygame.font.SysFont("consolas", 48, bold=True)
        self.mid = pygame.font.SysFont("consolas", 26, bold=True)

    def resize(self, cols: int, rows: int) -> None:
        """Resize the window when a new level has different dimensions."""
        width = cols * C.TILE_SIZE
        height = rows * C.TILE_SIZE + C.HUD_HEIGHT
        self.screen = pygame.display.set_mode((width, height))

    # ----- gameplay --------------------------------------------------------
    def draw_game(self, g: "Game") -> None:
        """Render the maze, dots, entities and HUD for the active game."""
        self.screen.fill(C.COLOR_BG)
        self._draw_maze(g.level.grid)
        self._draw_dots(g.level.pacgums, C.COLOR_PACGUM, 3)
        self._draw_dots(g.level.super_pacgums, C.COLOR_SUPER, 7)
        for ghost in g.ghosts:
            self._draw_ghost(ghost)
        self._draw_player(g.player)
        self._draw_hud(g)
        if g.state is GameState.PAUSED:
            self._overlay("PAUSED", "Press P to resume, M for menu")

    def _draw_maze(self, grid: List[List[int]]) -> None:
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == C.WALL:
                    rect = pygame.Rect(x * C.TILE_SIZE, y * C.TILE_SIZE,
                                       C.TILE_SIZE, C.TILE_SIZE)
                    pygame.draw.rect(self.screen, C.COLOR_WALL, rect)

    def _draw_dots(self, dots: Iterable[Tile],
                   color: Tuple[int, int, int], radius: int) -> None:
        for x, y in dots:
            cx = x * C.TILE_SIZE + C.TILE_SIZE // 2
            cy = y * C.TILE_SIZE + C.TILE_SIZE // 2
            pygame.draw.circle(self.screen, color, (cx, cy), radius)

    def _draw_player(self, player: "Player") -> None:
        px, py = player.pixel_pos
        cx = int(px * C.TILE_SIZE + C.TILE_SIZE / 2)
        cy = int(py * C.TILE_SIZE + C.TILE_SIZE / 2)
        radius = C.TILE_SIZE // 2 - 2
        # Animate the mouth with a simple time-based opening angle.
        t = pygame.time.get_ticks() / 1000.0
        mouth = (math.sin(t * 12) * 0.5 + 0.5) * 0.6 + 0.05
        facing = {
            (0, -1): -math.pi / 2, (0, 1): math.pi / 2,
            (-1, 0): math.pi, (1, 0): 0.0,
        }.get((player.direction.dx, player.direction.dy), 0.0)
        start = facing + mouth
        end = facing + 2 * math.pi - mouth
        points: List[Tuple[float, float]] = [(float(cx), float(cy))]
        steps = 20
        for i in range(steps + 1):
            ang = start + (end - start) * i / steps
            points.append((cx + radius * math.cos(ang),
                           cy + radius * math.sin(ang)))
        pygame.draw.polygon(self.screen, C.COLOR_PLAYER, points)

    def _draw_ghost(self, ghost: "Ghost") -> None:
        gx, gy = ghost.pixel_pos
        x = int(gx * C.TILE_SIZE)
        y = int(gy * C.TILE_SIZE)
        size = C.TILE_SIZE
        if ghost.eaten:
            color = C.COLOR_EATEN
        elif ghost.frightened:
            color = C.COLOR_FRIGHT
        else:
            color = C.GHOST_COLORS[ghost.color_index % len(C.GHOST_COLORS)]
        body = pygame.Rect(x + 2, y + 2, size - 4, size - 4)
        pygame.draw.rect(self.screen, color, body, border_radius=6)
        eye = max(2, size // 8)
        pygame.draw.circle(self.screen, (255, 255, 255),
                           (x + size // 3, y + size // 2), eye)
        pygame.draw.circle(self.screen, (255, 255, 255),
                           (x + 2 * size // 3, y + size // 2), eye)

    def _draw_hud(self, g: "Game") -> None:
        rows = g.level.height
        y0 = rows * C.TILE_SIZE
        bar = pygame.Rect(0, y0, self.screen.get_width(), C.HUD_HEIGHT)
        pygame.draw.rect(self.screen, (15, 15, 15), bar)
        cheat = "  [CHEAT]" if g.cheats.any_active() else ""
        text = (f"Score: {g.score}    Lives: {g.lives}    "
                f"Level: {g.level_index + 1}    "
                f"Time: {int(g.time_left)}{cheat}")
        label = self.font.render(text, True, C.COLOR_TEXT)
        self.screen.blit(label, (10, y0 + 10))

    # ----- menus / overlays ------------------------------------------------
    def draw_menu(self, scores: List[Tuple[str, int]],
                  message: str = "") -> None:
        """Render the main menu with the highscore table."""
        self.screen.fill(C.COLOR_BG)
        self._centered(self.big, "Pac-Man", C.COLOR_TITLE, 90)
        self._centered(self.mid, "Push SPACE to play", C.COLOR_TEXT, 170)
        self._centered(self.font, "I: instructions   ESC: quit",
                       C.COLOR_TEXT, 205)
        self._centered(self.font, "highscores:", C.COLOR_TEXT, 250)
        y = 280
        if not scores:
            self._centered(self.font, "- no scores yet -", C.COLOR_TEXT, y)
        for i, (name, score) in enumerate(scores, start=1):
            self._centered(self.font, f"{i}. {name} - {score} pts",
                           C.COLOR_TEXT, y)
            y += 26
        if message:
            self._centered(self.font, message, C.COLOR_SUPER, y + 20)
        pygame.display.flip()

    def draw_instructions(self) -> None:
        """Render the controls / rules screen."""
        self.screen.fill(C.COLOR_BG)
        lines = [
            "How to play",
            "",
            "Arrow keys or WASD : move",
            "P : pause / resume",
            "M : back to menu",
            "Eat all dots to clear the level.",
            "Super-pacgums make ghosts edible.",
            "",
            "Cheat keys (for review):",
            "F1 invincible   F2 skip level   F3 freeze ghosts",
            "F4 +1 life      F5 speed boost",
            "",
            "Press any key to go back",
        ]
        y = 60
        for line in lines:
            self._centered(self.font, line, C.COLOR_TEXT, y)
            y += 30
        pygame.display.flip()

    def draw_end(self, win: bool, score: int) -> None:
        """Render the game-over or victory screen."""
        self.screen.fill(C.COLOR_BG)
        if win:
            self._centered(self.big, "YOU WIN!", C.COLOR_PLAYER, 120)
        else:
            self._centered(self.big, "GAME OVER", (255, 60, 60), 120)
        self._centered(self.mid, f"Final score: {score}", C.COLOR_TEXT, 210)
        self._centered(self.font, "Press SPACE to continue",
                       C.COLOR_TEXT, 270)
        pygame.display.flip()

    def draw_name_entry(self, current: str, score: int) -> None:
        """Render the highscore name-entry prompt."""
        self.screen.fill(C.COLOR_BG)
        self._centered(self.mid, "New highscore!", C.COLOR_TITLE, 120)
        self._centered(self.font, f"Score: {score}", C.COLOR_TEXT, 175)
        self._centered(self.font, "Enter your name (max 10), then ENTER:",
                       C.COLOR_TEXT, 220)
        box = current + "_"
        self._centered(self.mid, box, C.COLOR_PLAYER, 260)
        pygame.display.flip()

    def _overlay(self, title: str, subtitle: str) -> None:
        veil = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 160))
        self.screen.blit(veil, (0, 0))
        self._centered(self.big, title, C.COLOR_TITLE, 140)
        self._centered(self.font, subtitle, C.COLOR_TEXT, 210)

    def _centered(self, font: "pygame.font.Font", text: str,
                  color: Tuple[int, int, int], y: int) -> None:
        label = font.render(text, True, color)
        rect = label.get_rect(center=(self.screen.get_width() // 2, y))
        self.screen.blit(label, rect)

    def flip(self) -> None:
        """Present the back buffer to the screen."""
        pygame.display.flip()
