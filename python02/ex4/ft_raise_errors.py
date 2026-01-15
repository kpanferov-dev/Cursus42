#!/usr/bin/env python3
"""
ft_raise_errors.py
Creating personal errors
"""


def check_plant_health(plant_name, water_level, sunlight_hours):
    """Function to check all stats of plant"""
    if plant_name.strip() == "" or plant_name is None:
        raise ValueError("Plant name cannot be empty!\n")

    if water_level < 1:
        raise ValueError(f"Water level {water_level} is too low (min 1)\n")
    elif water_level > 10:
        raise ValueError(f"Water level {water_level} is too high (max 10)\n")

    if sunlight_hours < 2:
        raise ValueError(f"Sunlight hours {sunlight_hours}" +
                         " is too low (min 2)\n")
    elif sunlight_hours > 12:
        raise ValueError("Sunlight hours" +
                         f"{sunlight_hours} is too high (max 12)\n")

    return f"Plant '{plant_name}' is healthy!\n"


def test_plant_checks():
    """Function to test all values"""
    print("=== Garden Plant Health Checker ===\n")

    print("Testing good values...")
    try:
        result = check_plant_health("tomato", 5, 6)
        print(result)
    except ValueError as e:
        print(f"Error: {e}")

    print("Testing empty plant name...")
    try:
        result = check_plant_health("", 5, 6)
        print(result)
    except ValueError as e:
        print(f"Error: {e}")

    print("Testing bad water level...")
    try:
        result = check_plant_health("lettuce", 15, 6)
        print(result)
    except ValueError as e:
        print(f"Error: {e}")

    print("Testing bad sunlight hours...")
    try:
        result = check_plant_health("carrot", 5, 0)
        print(result)
    except ValueError as e:
        print(f"Error: {e}")

    print("All error raising tests completed!")


test_plant_checks()
