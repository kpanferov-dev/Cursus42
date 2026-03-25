"""
render.py

Defines the abstract rendering contract for maze visualization.
"""

from abc import ABC, abstractmethod
from mazegen.maze import Maze


class Render(ABC):
    """
    Abstract base class for maze rendering implementations.

    Any subclass must implement the draw_maze method to define
    how a maze should be rendered (e.g., console, GUI, web, etc.).
    """

    @abstractmethod
    def draw_maze(self, maze: Maze) -> None:
        """
        Render the given maze.

        Args:
            maze: The maze object to be rendered. The expected
                  structure depends on the concrete implementation.

        Raises:
            NotImplementedError: If the method is not implemented
                                 by a subclass.
        """
        pass
