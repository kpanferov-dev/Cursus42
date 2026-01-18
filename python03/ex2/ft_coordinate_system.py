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


def main():
    """Main function"""
    print("=== Game Coordinate System ===\n")

    position = creat_position(0, 0, 0)
    position2 = creat_position(10, 20, 5)
    print(f"Position created: {position2}")
    distance = calculate_distance(position, position2)
    print(f"Distance between {position} and {position2}: {distance:.2f}\n")

    coordinates_str = "3,4,0"
    print(f'Parsing coordinates: "{coordinates_str}"')
    try:
        parsed_position = parse_coordinates(coordinates_str)
        print(f"Parsed position: {parsed_position}")
        distance = calculate_distance((0, 0, 0), parsed_position)
        print("Distance between (0, 0, 0)" +
              f" and {parsed_position}: {distance:.1f}\n")
    except ValueError as e:
        print(e)

    coordinates_str = "abc,def,ghi"
    print(f'Parsing invalid coordinates: "{coordinates_str}"')
    try:
        parsed_position2 = parse_coordinates(coordinates_str)
        print(f"{parsed_position2}")
    except ValueError as e:
        print(e)

    print("\nUnpacking demonstration:")
    x, y, z = parsed_position
    print(f"Player at x={parsed_position[0]}," +
          f" y={parsed_position[1]}, z={parsed_position[2]}")
    print(f"Coordinates: X={x}, Y={y}, Z={z}")


main()
