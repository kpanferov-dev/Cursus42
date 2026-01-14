#!/usr/bin/env python3

class Plant:
    def __init__(self, name: str, height: int, age: int):
        self.__name = name
        self.__height = height
        self.__age = age

    def get_name(self):
        return self.__name

    def get_height(self):
        return self.__height

    def get_age(self):
        return self.__age

    def get_info(self):
        return (
            f"{self.get_name()} ({self.__class__.__name__}): "
            f"{self.get_height()}cm, {self.get_age()} days"
        )


class Flower(Plant):
    def __init__(self, name: str, height: int, age: int, color: str):
        super().__init__(name, height, age)
        self.__color = color

    def get_color(self):
        return self.__color

    def bloom(self):
        return f"{self.get_name()} is blooming beautifully!"

    def get_info(self):
        return super().get_info() + f", {self.get_color()} color"


class Tree(Plant):
    def __init__(self, name: str, height: int, age: int, trunk_diameter: int):
        super().__init__(name, height, age)
        self.__trunk_diameter = trunk_diameter

    def get_trunk_diameter(self):
        return self.__trunk_diameter

    def produce_shade(self):
        return f"{self.get_name()} provides 78 square meters of shade"

    def get_info(self):
        return super().get_info() + f", {self.get_trunk_diameter()}cm diameter"


class Vegetable(Plant):
    def __init__(self, name: str, height: int, age: int,
                 harvest_season: str, nutritional_value: str):
        super().__init__(name, height, age)
        self.__harvest_season = harvest_season
        self.__nutritional_value = nutritional_value

    def get_harvest_season(self):
        return self.__harvest_season

    def get_nutritional_value(self):
        return (
                f"{self.get_name()} is rich in vitamin "
                f"{self.__nutritional_value}"
        )

    def get_info(self):
        return super().get_info() + f", {self.__harvest_season} harvest"


p1 = Flower("Rose", 25, 30, "red")
p2 = Tree("Oak", 500, 1825, 50)
p3 = Vegetable("Tomato", 80, 90, "summer", "C")

p11 = Flower("Sunflower", 25, 30, "yellow")
p22 = Tree("Pine", 500, 1825, 50)
p33 = Vegetable("Potato", 80, 90, "winter", "B, C , D")
print("=== Garden Plant Types ===\n")
print(p1.get_info())
print(p1.bloom())
print()
print(p2.get_info())
print(p2.produce_shade())
print()
print(p3.get_info())
print(p3.get_nutritional_value())
