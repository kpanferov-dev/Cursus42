"""The :class:`Game` orchestrates everything: state machine and main loop.

It owns the configuration, the highscore manager, the renderer, the current
level and all entities, and it drives transitions between the menu, gameplay,
pause, game-over and victory screens.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any, Dict, List

import pygame

from . import constants as C
from .constants import Direction, GameState
from .entities import Ghost, Player
from .highscore import HighScores
from .level import Level
from .maze_loader import MazeError, load_maze
from .ui import Renderer

FRIGHT_SECONDS: float = 7.0
PLAYER_BASE_SPEED: float = 0.12
PLAYER_BOOST_SPEED: float = 0.20

_KEY_DIRS = {
    pygame.K_UP: Direction.UP, pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN, pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT, pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT, pygame.K_d: Direction.RIGHT,
}


@dataclass
class Cheats:
    """Holds the toggleable cheat flags used during peer review."""

    invincible: bool = False
    freeze_ghosts: bool = False
    speed_boost: bool = False

    def any_active(self) -> bool:
        """True when at least one cheat is currently enabled."""
        return self.invincible or self.freeze_ghosts or self.speed_boost


class Game:
    """Top-level application object running the whole game loop."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialise pygame and prepare the main menu."""
        pygame.init()
        self.config = config
        self.scores = HighScores(config["highscore_filename"])
        self.clock = pygame.time.Clock()
        self.levels_cfg: List[Dict[str, int]] = config["levels"]
        self.renderer = Renderer(45, 45)     # provisional; resized per level
        self.state = GameState.MENU
        self.menu_message = ""
        self.name_buffer = ""
        self.pending_win = False

        self.level_index = 0
        self.score = 0
        self.lives = int(config["lives"])
        self.time_left = float(config["level_max_time"])
        self.fright_timer = 0.0
        self.cheats = Cheats()
        self.level: Level
        self.player: Player
        self.ghosts: List[Ghost] = []

    # ----- level setup -----------------------------------------------------
    def _build_level(self, index: int) -> bool:
        """Generate and install level *index*. Returns False on failure."""
        cfg = self.levels_cfg[index]
        # First level uses the fixed seed; later levels are random (seed 0).
        seed = int(self.config["seed"]) if index == 0 else 0
        try:
            maze = load_maze(cfg["width"], cfg["height"], seed)
        except MazeError as error:
            print(f"[game] cannot build level {index + 1}: {error}")
            self.menu_message = "Maze generation failed - check the package."
            return False
        self.level = Level(maze)
        self.renderer.resize(self.level.width, self.level.height)
        speed = PLAYER_BOOST_SPEED if self.cheats.speed_boost \
            else PLAYER_BASE_SPEED
        self.player = Player(self.level.player_start, speed)
        self.ghosts = [Ghost(tile, i)
                       for i, tile in enumerate(self.level.ghost_starts)]
        self.time_left = float(self.config["level_max_time"])
        self.fright_timer = 0.0
        return True

    def _start_new_game(self) -> None:
        """Reset score/lives and load the first level."""
        self.level_index = 0
        self.score = 0
        self.lives = int(self.config["lives"])
        self.cheats = Cheats()
        if self._build_level(0):
            self.state = GameState.PLAYING
        else:
            self.state = GameState.MENU

    def _respawn(self) -> None:
        """Place player and ghosts back at their start tiles."""
        self.player.reset(self.level.player_start)
        for ghost in self.ghosts:
            ghost.reset()
        self.fright_timer = 0.0

    # ----- the main loop ---------------------------------------------------
    def run(self) -> None:
        """Run until the player quits; never raises to the caller."""
        try:
            while True:
                dt = self.clock.tick(C.FPS) / 1000.0
                self._handle_events()
                if self.state is GameState.PLAYING:
                    self._update(dt)
                self._render()
        except KeyboardInterrupt:
            pass
        finally:
            pygame.quit()

    def _quit(self) -> None:
        pygame.quit()
        sys.exit(0)

    # ----- event handling --------------------------------------------------
    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit()
            elif event.type == pygame.KEYDOWN:
                self._on_key(event)

    def _on_key(self, event: "pygame.event.Event") -> None:
        if self.state is GameState.MENU:
            self._menu_key(event.key)
        elif self.state is GameState.PLAYING:
            self._play_key(event)
        elif self.state is GameState.PAUSED:
            self._pause_key(event.key)
        elif self.state in (GameState.GAME_OVER, GameState.VICTORY):
            if event.key == pygame.K_SPACE:
                self._after_end()
        elif self.state is GameState.ENTER_NAME:
            self._name_key(event)

    def _menu_key(self, key: int) -> None:
        if key == pygame.K_SPACE:
            self._start_new_game()
        elif key == pygame.K_i:
            self._show_instructions()
        elif key == pygame.K_ESCAPE:
            self._quit()

    def _show_instructions(self) -> None:
        """Blocking helper: show controls until a key is pressed."""
        self.renderer.draw_instructions()
        waiting = True
        while waiting:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit()
                if event.type == pygame.KEYDOWN:
                    waiting = False
            self.clock.tick(30)
        self.menu_message = ""

    def _play_key(self, event: "pygame.event.Event") -> None:
        key = event.key
        if key in _KEY_DIRS:
            self.player.request(_KEY_DIRS[key])
        elif key == pygame.K_p:
            self.state = GameState.PAUSED
        elif key == pygame.K_m:
            self.state = GameState.MENU
        else:
            self._cheat_key(key)

    def _cheat_key(self, key: int) -> None:
        if key == pygame.K_F1:
            self.cheats.invincible = not self.cheats.invincible
        elif key == pygame.K_F2:
            self._level_cleared()
        elif key == pygame.K_F3:
            self.cheats.freeze_ghosts = not self.cheats.freeze_ghosts
        elif key == pygame.K_F4:
            self.lives += 1
        elif key == pygame.K_F5:
            self.cheats.speed_boost = not self.cheats.speed_boost
            self.player.speed = (PLAYER_BOOST_SPEED
                                 if self.cheats.speed_boost
                                 else PLAYER_BASE_SPEED)

    def _pause_key(self, key: int) -> None:
        if key == pygame.K_p:
            self.state = GameState.PLAYING
        elif key == pygame.K_m:
            self.state = GameState.MENU

    def _name_key(self, event: "pygame.event.Event") -> None:
        if event.key == pygame.K_RETURN:
            self.scores.add(self.name_buffer, self.score)
            self.menu_message = "Score saved!"
            self.state = GameState.MENU
        elif event.key == pygame.K_BACKSPACE:
            self.name_buffer = self.name_buffer[:-1]
        elif len(self.name_buffer) < 10 and event.unicode.isprintable():
            ch = event.unicode
            if ch.isalnum() or ch == " ":
                self.name_buffer += ch

    def _after_end(self) -> None:
        """Decide whether to ask for a name after a game ends."""
        if self.scores.qualifies(self.score):
            self.name_buffer = ""
            self.state = GameState.ENTER_NAME
        else:
            self.state = GameState.MENU

    # ----- gameplay update -------------------------------------------------
    def _update(self, dt: float) -> None:
        self.time_left -= dt
        if self.time_left <= 0:
            self._lose_life()
            return
        if self.fright_timer > 0:
            self.fright_timer -= dt
            if self.fright_timer <= 0:
                for ghost in self.ghosts:
                    ghost.set_frightened(False)

        self.player.update(self.level.grid)
        self._eat_dots()
        now = pygame.time.get_ticks()

        for ghost in self.ghosts:
            if ghost.hidden and now >= ghost.respawn_time:
                ghost.reset()
                ghost.hidden = False
        for ghost in self.ghosts:
            if not ghost.hidden:
                ghost.update(self.level.grid, self.player.tile,
                             self.cheats.freeze_ghosts)
        self._check_collisions()
        if self.level.cleared:
            self._level_cleared()

    def _eat_dots(self) -> None:
        kind = self.level.eat(self.player.tile)
        if kind == "pacgum":
            self.score += int(self.config["points_per_pacgum"])
        elif kind == "super":
            self.score += int(self.config["points_per_super_pacgum"])
            self.fright_timer = FRIGHT_SECONDS
            for ghost in self.ghosts:
                ghost.set_frightened(True)

    def _check_collisions(self) -> None:
        for ghost in self.ghosts:
            if ghost.tile != self.player.tile or ghost.eaten or ghost.hidden:
                continue
            if ghost.frightened:
                ghost.get_eaten()
                ghost.respawn_time = pygame.time.get_ticks() + 1
                self.score += int(self.config["points_per_ghost"])
            elif not self.cheats.invincible:
                self._lose_life()
                return

    def _lose_life(self) -> None:
        self.lives -= 1
        if self.lives <= 0:
            self.pending_win = False
            self.state = GameState.GAME_OVER
        else:
            self._respawn()

    def _level_cleared(self) -> None:
        self.level_index += 1
        if self.level_index >= len(self.levels_cfg):
            self.pending_win = True
            self.state = GameState.VICTORY
            return
        if not self._build_level(self.level_index):
            self.state = GameState.GAME_OVER

    # ----- rendering dispatch ---------------------------------------------
    def _render(self) -> None:
        if self.state is GameState.MENU:
            self.renderer.draw_menu(self.scores.top(), self.menu_message)
        elif self.state in (GameState.PLAYING, GameState.PAUSED):
            self.renderer.draw_game(self)
            self.renderer.flip()
        elif self.state is GameState.GAME_OVER:
            self.renderer.draw_end(False, self.score)
        elif self.state is GameState.VICTORY:
            self.renderer.draw_end(True, self.score)
        elif self.state is GameState.ENTER_NAME:
            self.renderer.draw_name_entry(self.name_buffer, self.score)
