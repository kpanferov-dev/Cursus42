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


def garden_operations():
    """Function to catch errors"""
    print("Testing Plant Error...")
    try:
        raise PlantError
    except PlantError as e:
        print("Caught PlantError: ", e)

    print("\nTesting WaterError...")
    try:
        raise WaterError
    except WaterError as e:
        print("Caught WaterError: ", e)

    print("\nTesting catching all garden errors...")
    try:
        raise PlantError
    except GardenError as e:
        print("Caught a garden error: ", e)
    try:
        raise WaterError
    except GardenError as e:
        print("Caught a garden error: ", e)


def test_error():
    """Function to test all errors"""
    print("=== Custom Garden Errors Demo ===\n")
    garden_operations()
    print("\nAll custom error types work correctly!")


test_error()
