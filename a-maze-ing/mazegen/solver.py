"""Maze solving utilities."""

from collections import deque
from typing import Dict, List, Optional, Tuple

from mazegen.maze import Maze

Pos = Tuple[int, int]


def shortest_path(maze: Maze) -> Optional[List[Pos]]:
    """Compute the shortest path in a maze using BFS.

    This function finds the shortest path from the maze entry
    to the exit using Breadth-First Search (BFS).

    Args:
        maze (Maze): Maze instance to solve.

    Returns:
        Optional[List[Pos]]: List of positions representing the path
        from entry to exit, or None if no path exists.
    """
    start = maze.entry
    goal = maze.exit

    if (
        maze.get_cell(*start).is_fixed()
        or maze.get_cell(*goal).is_fixed()
    ):
        return None

    queue = deque([start])
    prev: Dict[Pos, Optional[Pos]] = {start: None}

    while queue:
        x, y = queue.popleft()

        if (x, y) == goal:
            break

        cell = maze.get_cell(x, y)
        candidates = [
            ("N", (x, y - 1)),
            ("S", (x, y + 1)),
            ("W", (x - 1, y)),
            ("E", (x + 1, y)),
        ]

        for direction, (nx, ny) in candidates:
            if not (0 <= nx < maze.width and 0 <= ny < maze.height):
                continue

            if cell.has_wall(direction):
                continue

            neighbor = maze.get_cell(nx, ny)
            if neighbor.is_fixed():
                continue

            pos = (nx, ny)
            if pos in prev:
                continue

            prev[pos] = (x, y)
            queue.append(pos)

    if goal not in prev:
        return None

    path: List[Pos] = []
    current: Optional[Pos] = goal

    while current is not None:
        path.append(current)
        current = prev[current]

    path.reverse()
    return path


def path_to_directions(path: List[Pos]) -> str:
    """Convert a path into a string of directions.

    Args:
        path (List[Pos]): List of positions representing a path.

    Returns:
        str: String of directions (e.g., "NSWE").

    Raises:
        ValueError: If the path contains non-adjacent steps.
    """
    directions: List[str] = []

    for (x1, y1), (x2, y2) in zip(path, path[1:]):
        dx = x2 - x1
        dy = y2 - y1

        if dx == 1 and dy == 0:
            directions.append("E")
        elif dx == -1 and dy == 0:
            directions.append("W")
        elif dx == 0 and dy == 1:
            directions.append("S")
        elif dx == 0 and dy == -1:
            directions.append("N")
        else:
            raise ValueError(
                "Non-adjacent step in path: "
                f"{(x1, y1)} -> {(x2, y2)}"
            )

    return "".join(directions)


def save_solution(
    maze: Maze,
    path: Optional[List[Pos]],
    file_path: str,
) -> bool:
    """Save the maze solution to a file.

    The maze is first saved in hexadecimal format, followed by
    the shortest path encoded as a direction string.

    Args:
        maze (Maze): Maze instance.
        path (Optional[List[Pos]]): Path to save.
        file_path (str): Output file path.

    Returns:
        bool: True if the solution was saved, False otherwise.
    """
    if not path:
        return False

    maze.save_hex(file_path)

    directions = path_to_directions(path)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(directions)

    return True
