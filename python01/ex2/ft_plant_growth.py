#!/usr/bin/env python3
"""
ft_plant_growth.py
A script to define a Plant class with growth and aging functionality.
"""


class Plant:
    """A class to represent a plant with a name, height, and age in days."""

    def __init__(self, name: str, height: int, age_in_days: int):
        """Initialize a plant with a name, height in cm, and age in days."""
        self.name = name
        self.height = height
        self.age_in_days = age_in_days

    def grow(self, growth_amount: int):
        """Increase the height of the plant."""
        self.height += growth_amount

    def age(self, age_increment: int):
        """Increase the age of the plant in days."""
        self.age_in_days += age_increment

    def get_info(self):
        """Print the plant's information."""
        print(f"{self.name}: {self.height}cm, {self.age_in_days} days old")


day = 1
growth_days = 6
p1 = Plant("Rose", 25, 30)
print(f"=== Day {day} ===")
p1.get_info()
day += growth_days
print(f"=== Day {day} ===")
p1.grow(growth_days)
p1.age(growth_days)
p1.get_info()
print(f"Growth this week: +{growth_days}cm")
