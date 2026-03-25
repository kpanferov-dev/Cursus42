"""
cell.py
File that contains Cell class
"""
from .constants import WALL_MASKS


class Cell:
    """
    Represents a single cell in a maze grid.

    Each cell knows its position (x, y), which walls are present, and whether
    it has been visited or is part of the solution path.

    Walls are stored as a 4-bit integer (bitmask) with bits representing:
        0 (LSB) - North
        1       - East
        2       - South
        3       - West

    Attributes:
        x (int): X-coordinate (column) of the cell.
        y (int): Y-coordinate (row) of the cell.
        __walls (int): Bitmask storing the presence of walls.
        __visited (bool): True if the cell has
        been visited during generation or solving.
        __is_path (bool): True if the cell is part of the solution path.
    """

    def __init__(self, x: int, y: int) -> None:
        """
        Initialize a Cell at coordinates (x, y) with all walls present.

        Args:
            x (int): Column index of the cell.
            y (int): Row index of the cell.
        """
        self.x = x
        self.y = y
        self.__walls = 0b1111
        self.__visited = False
        self.__is_path = False
        self.__is_fixed = False

    def set_as_fixed(self) -> None:
        """Mark the cell as fixed (non-modifiable).

        Fixed cells are typically used for special patterns
        (e.g., logos) and should not be altered during maze
        generation or solving.
        """
        self.__is_fixed = True

    def is_fixed(self) -> bool:
        """Check whether the cell is fixed.

        Returns:
            bool: True if the cell is fixed, False otherwise.
        """
        return self.__is_fixed

    def _get_mask(self, direction: str) -> int:
        """
        Get the bitmask corresponding to a direction.

        Args:
            direction (str): One of 'N', 'E', 'S', 'W'.

        Returns:
            int: Bitmask of the specified wall.

        Raises:
            ValueError: If the direction is invalid.
        """
        try:
            return WALL_MASKS[direction]
        except KeyError:
            raise ValueError(f"Invalid direction: {direction}")

    def remove_wall(self, direction: str) -> None:
        """
        Remove a wall in the given direction.

        Args:
            direction (str): One of 'N', 'E', 'S', 'W'.
        """
        mask = self._get_mask(direction)
        self.__walls &= ~mask

    def add_wall(self, direction: str) -> None:
        """
        Add a wall in the given direction.

        Args:
            direction (str): One of 'N', 'E', 'S', 'W'.
        """
        mask = self._get_mask(direction)
        self.__walls |= mask

    def has_wall(self, direction: str) -> bool:
        """
        Check if there is a wall in the given direction.

        Args:
            direction (str): One of 'N', 'E', 'S', 'W'.

        Returns:
            bool: True if the wall is present, False otherwise.
        """
        mask = self._get_mask(direction)
        return bool(self.__walls & mask)

    def is_closed(self) -> bool:
        """
        Check if all walls are present (cell is fully closed).

        Returns:
            bool: True if all walls are present.
        """
        return self.__walls == 0b1111

    def is_open(self) -> bool:
        """
        Check if all walls are removed (cell is fully open).

        Returns:
            bool: True if no walls are present.
        """
        return self.__walls == 0b0000

    @property
    def walls(self) -> int:
        """
        Get the current walls bitmask.

        Returns:
            int: 4-bit integer representing the walls.
        """
        return self.__walls

    @property
    def visited(self) -> bool:
        """
        Whether the cell has been visited.

        Returns:
            bool
        """
        return self.__visited

    @visited.setter
    def visited(self, value: bool) -> None:
        """
        Set the visited status of the cell.

        Args:
            value (bool): True if visited, False otherwise.

        Raises:
            ValueError: If value is not a boolean.
        """
        if not isinstance(value, bool):
            raise ValueError("Visited must be a boolean")
        self.__visited = value

    @property
    def path(self) -> bool:
        """
        Whether the cell is part of the solution path.

        Returns:
            bool
        """
        return self.__is_path

    @path.setter
    def path(self, value: bool) -> None:
        """
        Set whether the cell is part of the solution path.

        Args:
            value (bool): True if part of the path, False otherwise.

        Raises:
            ValueError: If value is not a boolean.
        """
        if not isinstance(value, bool):
            raise ValueError("Path must be a boolean")
        self.__is_path = value

    def to_hex(self) -> str:
        """
        Return the walls as a single hexadecimal digit (0-F).

        Useful for saving the maze to a file.

        Returns:
            str: Hexadecimal representation of the walls.
        """
        return f"{self.__walls:X}"
