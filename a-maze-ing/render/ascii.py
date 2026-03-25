"""ASCII-based renderer for maze visualization."""

import time
from typing import List, Optional, Tuple

from mazegen.maze import Maze
from mazegen.solver import shortest_path, save_solution
from mazegen.maze_generator import MazeGenerator, InvalidEntryOrExit

from .render import Render

Pos = Tuple[int, int]


class AsciiRender(Render):
    """Render a maze in the terminal using ASCII characters.

    This renderer provides an interactive command-line interface
    to visualize and interact with a maze. It supports features such as
    path visualization, color toggling, and animation.

    Attributes:
        file_path (str): Output file where the solution is saved.
        show_path (bool): Whether to display the shortest path.
        use_color (bool): Enable or disable ANSI colors.
        colorize_logo_42 (bool): Toggle coloring for fixed cells.
        animate_path (bool): Enable path animation.
        path_delay (float): Delay between animation steps (seconds).
    """

    def __init__(self, file_path: str) -> None:
        """Initialize the ASCII renderer.

        Args:
            file_path (str): Path to save the solution file.
        """
        self.file_path = file_path

        # toggles
        self.show_path = False
        self.use_color = True
        self.colorize_logo_42 = True

        # animation
        self.animate_path = True
        self.path_delay = 0.02

        # wall color palettes (ANSI)
        self.wall_palettes = [
            "\x1b[37m",  # white
            "\x1b[36m",  # cyan
            "\x1b[31m",  # red
            "\x1b[32m",  # green
            "\x1b[33m",  # yellow
        ]
        self.wall_palette_index = 0

        # extra colors
        self.reset = "\x1b[0m"
        self.logo_42_color = "\x1b[35m"
        self.path_color = "\x1b[93m"

        self._cached_path: Optional[List[Pos]] = None

    def run(
        self,
        maze: Maze,
        *,
        generator: MazeGenerator,
        algorithm: str = "dfs",
        seed: int = 1,
        apply_logo_42: bool = False,
    ) -> None:
        """Start the interactive ASCII rendering loop.

        Supported commands:
            r: regenerate maze
            p: toggle shortest path display
            a: toggle path animation
            c: change wall color
            l: toggle logo color
            color: toggle ANSI colors
            q: quit

        Args:
            maze (Maze): Maze to render.
            generator (MazeGenerator): Maze generator instance.
            algorithm (str, optional): Generation algorithm.
                Defaults to "dfs".
            seed (int, optional): Random seed. Defaults to 1.
            apply_logo_42 (bool, optional): Apply logo overlay.
        """
        save_solution(maze, shortest_path(maze), self.file_path)

        while True:
            self._clear()

            path = None
            if self.show_path:
                if self._cached_path is None:
                    self._cached_path = shortest_path(maze)
                path = self._cached_path

            self.draw_maze(maze, path=path)
            self._print_menu()

            cmd = input("> ").strip().lower()

            if cmd in ("q", "quit", "exit"):
                return

            if cmd == "r":
                new_maze = Maze(
                    width=maze.width,
                    height=maze.height,
                    perfect=maze.perfect,
                    seed=maze.seed,
                    entry=maze.entry,
                    exit=maze.exit,
                )

                if apply_logo_42:
                    try:
                        generator.set_logo_42(new_maze)
                    except InvalidEntryOrExit:
                        pass

                generator.generate_maze(new_maze, algorithm)
                maze = new_maze
                self._cached_path = None

                save_solution(
                    maze,
                    shortest_path(maze),
                    self.file_path,
                )

                if self.show_path:
                    self._cached_path = shortest_path(maze)
                    if self.animate_path and self._cached_path:
                        self._animate_path_once(
                            maze,
                            self._cached_path,
                        )

            elif cmd == "p":
                self.show_path = not self.show_path

                if self.show_path:
                    self._cached_path = shortest_path(maze)
                    if self.animate_path and self._cached_path:
                        self._animate_path_once(
                            maze,
                            self._cached_path,
                        )

            elif cmd == "c":
                self.wall_palette_index = (
                    (self.wall_palette_index + 1)
                    % len(self.wall_palettes)
                )

            elif cmd == "l":
                self.colorize_logo_42 = (
                    not self.colorize_logo_42
                )

            elif cmd in ("color", "ansi"):
                self.use_color = not self.use_color

            elif cmd == "a":
                self.animate_path = not self.animate_path

    def draw_maze(
        self,
        maze: Maze,
        *,
        path: Optional[List[Pos]] = None,
    ) -> None:
        """Draw the maze in ASCII format.

        Args:
            maze (Maze): Maze to render.
            path (Optional[List[Pos]]): Optional path to highlight.
        """
        path_set = set(path or [])

        wall_color = (
            self.wall_palettes[self.wall_palette_index]
            if self.use_color else ""
        )
        reset = self.reset if self.use_color else ""
        path_color = self.path_color if self.use_color else ""
        logo_color = (
            self.logo_42_color
            if (self.use_color and self.colorize_logo_42)
            else ""
        )

        def w(s: str) -> str:
            return f"{wall_color}{s}{reset}" if self.use_color else s

        def logo(s: str) -> str:
            return f"{logo_color}{s}{reset}" if logo_color else s

        def pch(s: str) -> str:
            return f"{path_color}{s}{reset}" if self.use_color else s

        top_line = w("+")
        for x in range(maze.width):
            cell = maze.get_cell(x, 0)
            if cell.is_fixed():
                top_line += logo("---") + w("+")
            else:
                top_line += (
                    w("---+") if cell.has_wall("N") else w("   +")
                )
        print(top_line)

        for y in range(maze.height):
            middle_line = ""
            for x in range(maze.width):
                cell = maze.get_cell(x, y)

                if cell.is_fixed():
                    middle_line += w("|")
                else:
                    middle_line += (
                        w("|") if cell.has_wall("W") else " "
                    )

                pos = (x, y)
                if pos == maze.entry:
                    middle_line += " x "
                elif pos == maze.exit:
                    middle_line += " o "
                elif pos in path_set and not cell.is_fixed():
                    middle_line += pch(" . ")
                else:
                    middle_line += (
                        logo("***") if cell.is_fixed() else "   "
                    )

            last_cell = maze.get_cell(maze.width - 1, y)
            middle_line += (
                w("|") if last_cell.has_wall("E") else " "
            )
            print(middle_line)

            bottom_line = w("+")
            for x in range(maze.width):
                cell = maze.get_cell(x, y)
                if cell.is_fixed():
                    bottom_line += logo("---") + w("+")
                else:
                    bottom_line += (
                        w("---+") if cell.has_wall("S")
                        else w("   +")
                    )
            print(bottom_line)

    def _animate_path_once(
        self,
        maze: Maze,
        path: List[Pos],
    ) -> None:
        """Animate the path step-by-step in the terminal.

        Args:
            maze (Maze): Maze to render.
            path (List[Pos]): Path to animate.
        """
        for k in range(1, len(path) + 1):
            self._clear()
            self.draw_maze(maze, path=path[:k])
            self._print_menu()
            time.sleep(self.path_delay)

    def _print_menu(self) -> None:
        """Display available user commands."""
        print()
        print(
            "Commands: [r] regenerate | [p] path on/off | "
            "[a] path anim on/off | [c] wall color | "
            "[l] 42 color | [color] ansi on/off | [q] quit"
        )

    def _clear(self) -> None:
        """Clear the terminal screen using ANSI escape codes."""
        print("\x1b[2J\x1b[H", end="")
