#!/usr/bin/env python3
"""
ft_garden_security.py
A script to manage and validate plant data using the SecurePlant class.
"""


class SecurePlant:
    """A plant class that ensures validity and safety of operations."""

    def __init__(self, name: str, height: int, age: int):
        """
        Initialize a plant with a name, height, and age.

        Ensures height and age values are non-negative. If invalid values
        are provided, the plant is marked as invalid.
        """
        if height < 0 or age < 0:
            print("Invalid plant values")
            self.__valid = False
            return
        self.__name = name
        self.__valid = True
        print(f"Plant created: {self.__name}")
        self.set_height(height)
        self.set_age(age)

    def get_height(self):
        """Return the plant's height in cm."""
        return self.__height

    def get_age(self):
        """Return the plant's age in days."""
        return self.__age

    def set_height(self, height: int):
        """
        Safely update the plant's height.

        Rejects negative values and updates the height only if the plant
        is marked as valid.
        """
        if height < 0:
            print(f"Invalid operation attempted: height {height}cm [REJECTED]")
        else:
            if self.__valid:
                print(f"Height updated: {height}cm [OK]")
                self.__height = height

    def set_age(self, age: int):
        """
        Safely update the plant's age.

        Rejects negative values and updates the age only if the plant
        is marked as valid.
        """
        if age < 0:
            print("Security: Negative age rejected")
        else:
            if self.__valid:
                print(f"Age updated: {age} days [OK]")
                self.__age = age

    def get_info(self):
        """
        Return information about the current plant.

        If the plant is valid, returns its name, height, and age. Otherwise,
        indicates that the plant does not exist.
        """
        if self.__valid:
            content = f"({self.get_height()}cm, {self.get_age()} days)"
            return f"Current plant: {self.__name} " + content
        else:
            return "Plant doesn´t exist"


print("=== Garden Security System ===")
plant = SecurePlant("Rose", 25, 30)
print()
plant.set_height(-5)
plant.set_age(-50)
print()
print(plant.get_info())
