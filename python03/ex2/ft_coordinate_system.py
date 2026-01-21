"""
ex2.ft_coordinate_system
Playing with tuples
"""


import math


def creat_position(x, y, z):
    """3d tuple inmutable"""
    try:
        x = int(x)
        y = int(y)
        z = int(z)
    except ValueError:
        raise ValueError(f"Invalid coordinates: ({x}, {y}, {z})." +
                         " All values must be numbers.")
    return (x, y, z)


def calculate_distance(point1, point2):
    """Calulate distance between 2 points"""
    x1, y1, z1 = point1
    x2, y2, z2 = point2
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)


def parse_coordinates(coordinate_string):
    """Parsing a string into a tuple"""
    parts = coordinate_string.split(",")
    if len(parts) != 3:
        raise ValueError("Coordinate string must have exactly 3 values.")
    try:
        x = int(parts[0])
        y = int(parts[1])
        z = int(parts[2])
        return (x, y, z)
    except ValueError as e:
        return (f"Error parsing coordinates: {e}." +
                f"\nError details - Type: ValueError, Args: {e.args}"
                )
