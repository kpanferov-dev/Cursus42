#!/usr/bin/env python3
"""
ft_custom_errors.py
Creating error Clases
"""


class GardenError(Exception):
    """General Errors"""
    def __init__(self, message="General error"):
        super().__init__(message)


class PlantError(GardenError):
    """Plant Errors"""
    def __init__(self, message="The tomato plant is wilting!"):
        super().__init__(message)


class WaterError(GardenError):
    """Water Errors"""
    def __init__(self, message="Not enough water in the tank!"):
        super().__init__(message)


def plant_problem():
    """Function that calls plant error message"""
    raise PlantError


def water_error():
    """Function that calls water error message"""
    raise WaterError


def test_errors():
    """Function to test all errors"""
    print("Testing Plant Error...")
    try:
        plant_problem()
    except PlantError as e:
        print("Caught PlantError: ", e)

    print("\nTesting WaterError...")
    try:
        water_error()
    except WaterError as e:
        print("Caught WaterError: ", e)

    print("\nTesting catching all garden errors...")
    try:
        plant_problem()
    except GardenError as e:
        print("Caught a garden error: ", e)
    try:
        water_error()
    except GardenError as e:
        print("Caught a garden error: ", e)


def main():
    print("=== Custom Garden Errors Demo ===\n")
    test_errors()
    print("\nAll custom error types work correctly!")


main()
