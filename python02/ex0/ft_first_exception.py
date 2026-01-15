#!/usr/bin/env python3
"""
ft_first_exception.py
First try / except program
"""


def check_temperature(temp_str):
    """Temperature checker"""
    try:
        temp = int(temp_str)
        if temp < 0:
            print(f"Error: {temp}°C is too cold for plants (min 0°C)\n")
            return None
        if temp > 40:
            print(f"Error: {temp}°C is too hot for plants (max 40°C)\n")
            return None
        return temp
    except ValueError:
        print(f"Error: '{temp_str}' is not a valid number\n")
        return None


def test_temperature_input():
    """Temperature tester"""
    test = [25, "abc", 100, -50]

    print("=== Garden Temperature Checker ===\n")
    for value in test:
        print(f"Testing temperature: {value}")
        if check_temperature(value) is not None:
            print(f"Temperature {value}°C is perfect for plants!\n")

    print("All tests completed - program didn't crash!")


test_temperature_input()
