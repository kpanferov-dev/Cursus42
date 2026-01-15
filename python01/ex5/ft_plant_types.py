#!/usr/bin/env python3
"""
ft_plant_types.py
A script to manage a variety of plant types,
including flowers, trees, and vegetables.
"""


class Plant:
    """A base class representing a plant with a name, height, and age."""

    def __init__(self, name: str, height: int, age: int):
        """Initialize the plant with a name, height in cm, and age in days."""
        self.__name = name
        self.__height = height
        self.__age = age

    def get_name(self):
        """Return the name of the plant."""
        return self.__name

    def get_height(self):
        """Return the height of the plant in cm."""
        return self.__height

    def get_age(self):
        """Return the age of the plant in days."""
        return self.__age

    def get_info(self):
        """Return a string containing the plant's basic information."""
        return (
            f"{self.get_name()} ({self.__class__.__name__}): "
            f"{self.get_height()}cm, {self.get_age()} days"
        )


class Flower(Plant):
    """A class representing a flower, extending the Plant class."""

    def __init__(self, name: str, height: int, age: int, color: str):
        """Initialize the flower with a name, height, age, and color."""
        super().__init__(name, height, age)
        self.__color = color

    def get_color(self):
        """Return the color of the flower."""
        return self.__color

    def bloom(self):
        """Simulate the blooming of the flower."""
        return f"{self.get_name()} is blooming beautifully!"

    def get_info(self):
        """Return a string containing the
        flower's information, including its color."""
        return super().get_info() + f", {self.get_color()} color"


class Tree(Plant):
    """A class representing a tree, extending the Plant class."""

    def __init__(self, name: str, height: int, age: int, trunk_diameter: int):
        """Initialize the tree with a name, height, age, and trunk diameter."""
        super().__init__(name, height, age)
        self.__trunk_diameter = trunk_diameter

    def get_trunk_diameter(self):
        """Return the trunk diameter of the tree in cm."""
        return self.__trunk_diameter

    def produce_shade(self):
        """Simulate the tree producing shade."""
        return f"{self.get_name()} provides 78 square meters of shade"

    def get_info(self):
        """Return a string containing the tree's
        information, including trunk diameter."""
        return super().get_info() + f", {self.get_trunk_diameter()}cm diameter"


class Vegetable(Plant):
    """A class representing a vegetable, extending the Plant class."""

    def __init__(self, name: str, height: int, age: int,
                 harvest_season: str, nutritional_value: str):
        """
        Initialize the vegetable with a name, height, age, harvest season,
        and nutritional value.
        """
        super().__init__(name, height, age)
        self.__harvest_season = harvest_season
        self.__nutritional_value = nutritional_value

    def get_harvest_season(self):
        """Return the harvest season of the vegetable."""
        return self.__harvest_season

    def get_nutritional_value(self):
        """Return a description of the vegetable's nutritional value."""
        return (
            f"{self.get_name()} is rich in vitamin "
            f"{self.__nutritional_value}"
        )

    def get_info(self):
        """Return a string containing the vegetable's
          information, including harvest season."""
        return super().get_info() + f", {self.__harvest_season} harvest"


# Instances of plants
p1 = Flower("Rose", 25, 30, "red")
p2 = Tree("Oak", 500, 1825, 50)
p3 = Vegetable("Tomato", 80, 90, "summer", "C")

p11 = Flower("Sunflower", 25, 30, "yellow")
p22 = Tree("Pine", 500, 1825, 50)
p33 = Vegetable("Potato", 80, 90, "winter", "B, C, D")

# Display garden plant information
print("=== Garden Plant Types ===\n")
print(p1.get_info())
print(p1.bloom())
print()
print(p2.get_info())
print(p2.produce_shade())
print()
print(p3.get_info())
print(p3.get_nutritional_value())
