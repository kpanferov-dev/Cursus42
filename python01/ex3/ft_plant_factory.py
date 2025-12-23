#!/usr/bin/env python3

class Plant:
    def __init__(self, name: str, height: int, age: int):
        self.name = name
        self.height = height
        self.age = age

    def get_info(self):
        print(f"Created: {self.name} ({self.height}cm, {self.age} days)")


plant_data = [
    ["Rose", 25, 30],
    ["Oak", 300, 365],
    ["Cactus", 5, 90],
    ["Sunflower", 80, 45],
    ["Fern", 15, 120]
]
factory = [Plant(name, height, age) for name, height, age in plant_data]
print("=== Plant Factory Output ===")
for plant in factory:
    plant.get_info()
print(f"\nTotal plants created: {len(factory)}")
