"""Maze generation algorithms and utilities."""

import random
from typing import Dict, List, Tuple

from .cell import Cell
from .maze import Maze


class InvalidEntryOrExit(Exception):
    """Exception raised when entry or exit overlaps with fixed cells."""
    pass


class MazeGenerator:
    """Generate mazes using different algorithms.

    This class provides multiple algorithms to generate mazes,
    such as DFS (backtracking), Prim, and Kruskal. It also supports
    adding custom patterns (e.g., the '42' logo) and non-perfect mazes.

    Attributes:
        _seed (int): Seed used for random generation.
    """

    def __init__(self, seed: int) -> None:
        """Initialize the maze generator.

        Args:
            seed (int): Random seed. If 0, randomness is not fixed.
        """
        self._seed = seed

    def generate_maze(self, maze: Maze, algorithm: str) -> None:
        """Generate a maze using the specified algorithm.

        Args:
            maze (Maze): Maze instance to modify.
            algorithm (str): Algorithm name ("dfs", "prim", "kruskal").

        Raises:
            ValueError: If the algorithm is unknown.
        """
        algorithm = algorithm.lower()

        if algorithm in ("dfs", "backtracking"):
            self._generate_dfs(maze)
        elif algorithm == "prim":
            self._generate_prim(maze)
        elif algorithm == "kruskal":
            self._generate_kruskal(maze)
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")

    def _init_random(self) -> None:
        """Initialize the random seed."""
        random.seed(None if self._seed == 0 else self._seed)

    def _carve_rooms(self, maze: Maze, attempts: int = 20) -> None:
        """Carve random rooms into a non-perfect maze.

        Args:
            maze (Maze): Maze instance.
            attempts (int, optional): Number of attempts. Defaults to 20.
        """
        room_sizes = [(2, 2), (2, 3), (3, 2)]

        def try_remove(cell: Cell, neighbor: Cell) -> None:
            if neighbor.is_fixed():
                return

            maze.remove_wall_between(cell, neighbor)

            if maze.has_invalid_room():
                maze.add_wall_between(cell, neighbor)

        def carve_one() -> None:
            w, h = random.choice(room_sizes)
            x = random.randint(0, maze.width - w)
            y = random.randint(0, maze.height - h)

            for dy in range(h):
                for dx in range(w):
                    cell = maze.get_cell(x + dx, y + dy)

                    if cell.is_fixed():
                        continue

                    if dx < w - 1:
                        right = maze.get_cell(x + dx + 1, y + dy)
                        try_remove(cell, right)

                    if dy < h - 1:
                        down = maze.get_cell(x + dx, y + dy + 1)
                        try_remove(cell, down)

        for _ in range(attempts):
            carve_one()

    def _generate_dfs(self, maze: Maze) -> None:
        """Generate a maze using Depth-First Search (backtracking)."""
        self._init_random()

        start_x = random.randint(0, maze.width - 1)
        start_y = random.randint(0, maze.height - 1)

        current_cell = maze.get_cell(start_x, start_y)
        current_cell.visited = True

        stack: List[Cell] = [current_cell]
        directions: List[Tuple[int, int]] = [
            (1, 0), (-1, 0), (0, 1), (0, -1)
        ]

        while stack:
            current_cell = stack[-1]
            unvisited_neighbors: List[Cell] = []

            for dx, dy in directions:
                nx = current_cell.x + dx
                ny = current_cell.y + dy

                if 0 <= nx < maze.width and 0 <= ny < maze.height:
                    neighbor = maze.get_cell(nx, ny)
                    if not neighbor.visited:
                        unvisited_neighbors.append(neighbor)

            if unvisited_neighbors:
                chosen = random.choice(unvisited_neighbors)
                maze.remove_wall_between(current_cell, chosen)
                chosen.visited = True
                stack.append(chosen)
            else:
                stack.pop()

        if not maze.perfect:
            self._carve_rooms(maze)

    def _generate_prim(self, maze: Maze) -> None:
        """Generate a maze using Prim's algorithm."""
        self._init_random()

        directions = [(0, -1), (0, 1), (1, 0), (-1, 0)]

        while True:
            x = random.randint(0, maze.width - 1)
            y = random.randint(0, maze.height - 1)
            start = maze.get_cell(x, y)
            if not start.is_fixed():
                break

        start.visited = True
        frontier: List[Cell] = []

        def add_frontier(cell: Cell) -> None:
            for dx, dy in directions:
                nx = cell.x + dx
                ny = cell.y + dy

                if 0 <= nx < maze.width and 0 <= ny < maze.height:
                    neighbor = maze.get_cell(nx, ny)
                    if not neighbor.visited and neighbor not in frontier:
                        frontier.append(neighbor)

        add_frontier(start)

        while frontier:
            current = frontier.pop(random.randrange(len(frontier)))

            visited_neighbors = []
            for dx, dy in directions:
                nx = current.x + dx
                ny = current.y + dy

                if 0 <= nx < maze.width and 0 <= ny < maze.height:
                    neighbor = maze.get_cell(nx, ny)
                    if neighbor.visited and not neighbor.is_fixed():
                        visited_neighbors.append(neighbor)

            if visited_neighbors:
                chosen = random.choice(visited_neighbors)
                maze.remove_wall_between(current, chosen)

            current.visited = True
            add_frontier(current)

        if not maze.perfect:
            self._carve_rooms(maze)

    def _generate_kruskal(self, maze: Maze) -> None:
        """Generate a maze using Kruskal's algorithm."""
        self._init_random()

        edges: List[Tuple[Cell, Cell]] = []

        for y in range(maze.height):
            for x in range(maze.width):
                cell = maze.get_cell(x, y)

                if cell.is_fixed():
                    continue

                if x < maze.width - 1:
                    right = maze.get_cell(x + 1, y)
                    if not right.is_fixed():
                        edges.append((cell, right))

                if y < maze.height - 1:
                    down = maze.get_cell(x, y + 1)
                    if not down.is_fixed():
                        edges.append((cell, down))

        random.shuffle(edges)

        parent: Dict[Cell, Cell] = {
            maze.get_cell(x, y): maze.get_cell(x, y)
            for y in range(maze.height)
            for x in range(maze.width)
        }

        def find(cell: Cell) -> Cell:
            if parent[cell] != cell:
                parent[cell] = find(parent[cell])
            return parent[cell]

        def union(c1: Cell, c2: Cell) -> None:
            parent[find(c2)] = find(c1)

        for c1, c2 in edges:
            if find(c1) != find(c2):
                union(c1, c2)
                maze.remove_wall_between(c1, c2)
                c1.visited = True
                c2.visited = True

        if not maze.perfect:
            self._carve_rooms(maze)

    def set_logo_42(self, maze: Maze) -> bool:
        """Embed a '42' logo pattern into the maze.

        Args:
            maze (Maze): Maze to modify.

        Returns:
            bool: True if applied, False if maze too small.

        Raises:
            InvalidEntryOrExit: If entry/exit overlaps the logo.
        """
        if maze.width < 9 or maze.height < 7:
            print("Size not enough for the 42 logo")
            return False

        pattern = [
            [1, 0, 1, 0, 1, 1, 1],
            [1, 0, 1, 0, 0, 0, 1],
            [1, 1, 1, 0, 1, 1, 1],
            [0, 0, 1, 0, 1, 0, 0],
            [0, 0, 1, 0, 1, 1, 1],
        ]

        start_x = (maze.width - len(pattern[0])) // 2
        start_y = (maze.height - len(pattern)) // 2

        for y, row in enumerate(pattern):
            for x, val in enumerate(row):
                if val == 1:
                    pos = (start_x + x, start_y + y)

                    if pos == maze.entry or pos == maze.exit:
                        raise InvalidEntryOrExit()

                    cell = maze.get_cell(*pos)
                    cell.set_as_fixed()
                    cell.visited = True

        return True
