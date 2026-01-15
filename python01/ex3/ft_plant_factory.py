#!/usr/bin/env python3
"""
ft_plant_factory.py
A script to create and manage plants using a factory pattern-like approach.
"""


class Plant:
    """A class to represent a plant with a name, height, and age."""

    def __init__(self, name: str, height: int, age: int):
        """Initialize a plant with a name, height in cm, and age in days."""
        self.name = name
        self.height = height
        self.age = age

    def get_info(self):
        """Print the plant's creation details."""
        print(f"Created: {self.name} ({self.height}cm, {self.age} days)")


plant_data = [
    ["Rose", 25, 30],
    ["Oak", 300, 365],
    ["Cactus", 5, 90],
    ["Sunflower", 80, 45],
    ["Fern", 15, 120]
]
num_plants = 0
factory = [Plant(name, height, age) for name, height, age in plant_data]
print("=== Plant Factory Output ===")
for plant in factory:
    num_plants += 1
    plant.get_info()
print(f"\nTotal plants created: {num_plants}")
