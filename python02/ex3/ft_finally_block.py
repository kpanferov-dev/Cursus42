#!/usr/bin/env python3
"""
ft_finally_block.py
Cleaning after finishing
"""


def water_plants(plant_list):
    """Watering plants function"""
    print("Opening watering system")
    try:
        for plant in plant_list:
            if not plant:
                raise ValueError(f"Cannot water {plant} - invalid plant!")
            print(f"Watering {plant}")
    except ValueError as e:
        print("Error:", e)
    finally:
        print("Closing watering system (cleanup)")


def test_watering_system():
    """Function that test everything"""
    print("=== Garden Watering System ===\n")
    print("Testing normal watering...")
    water_plants(["tomato", "lettuce", "carrots"])
    print("Watering completed successfully!\n")

    print("Testing with error...")
    water_plants(["tomato", None, None])
    print("\nCleanup always happens, even with errors!")


test_watering_system()
