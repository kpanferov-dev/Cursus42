#!/usr/bin/env python3
"""
ft_garden_analytics.py
A script to manage a garden system with different plant types.
This includes regular plants, flowering plants, and prize flowers.
It also manages gardens and calculates statistics.
"""


class Plant:
    """A base class representing a regular plant."""
    __type = "regular"

    def __init__(self, name: str, height: int):
        """Initialize a plant with a name and height."""
        self.set_name(name)
        self.set_height(height)

    def get_name(self):
        """Return the name of the plant."""
        return self.__name

    def get_height(self):
        """Return the height of the plant."""
        return self.__height

    def get_type(self):
        """Return the type of the plant."""
        return self.__type

    def set_name(self, name: str):
        """Set the name of the plant."""
        self.__name = name

    def set_height(self, height: int):
        """Set the height of the plant."""
        self.__height = height

    def grow(self, amount: int):
        """Increase the plant's height."""
        self.__height += amount

    def get_info(self):
        """Return the plant's information."""
        return f"- {self.get_name()}: {self.get_height()}cm"


class FloweringPlant(Plant):
    """A class representing a flowering plant."""
    __type = "flowering"

    def __init__(self, name: str,
                 height: int, color: str, blooming=True):
        """Initialize a flowering plant with a name,
          height, color, and blooming status."""
        super().__init__(name, height)
        self.set_color(color)
        self.set_blooming(blooming)

    def get_color(self):
        """Return the flower's color."""
        return self.__color

    def get_blooming(self):
        """Return whether the flower is blooming."""
        return "blooming" if self.__blooming else "not blooming"

    def get_type(self):
        """Return the type of the flowering plant."""
        return self.__type

    def set_color(self, color: str):
        """Set the color of the flower."""
        self.__color = color

    def set_blooming(self, blooming: bool):
        """Set the blooming status of the flower."""
        self.__blooming = blooming

    def get_info(self):
        """Return the flowering plant's information."""
        return (super().get_info() +
                f", {self.get_color()} flowers ({self.get_blooming()})"
                )


class PrizeFlower(FloweringPlant):
    """A class representing a prize-winning flower."""
    __type = "prize"

    def __init__(self, name: str, height: int,
                 color: str, points: int, blooming=True):
        """Initialize a prize flower with a name,
          height, color, points, and blooming status."""
        super().__init__(name, height, color, blooming)
        self.set_points(points)

    def get_points(self):
        """Return the prize points of the flower."""
        return self.__points

    def get_type(self):
        """Return the type of the prize flower."""
        return self.__type

    def set_points(self, points):
        """Set the prize points of the flower."""
        self.__points = points

    def get_info(self):
        """Return the prize flower's information."""
        return super().get_info() + f", Prize points: {self.get_points()}"


class Garden:
    """A class representing a garden."""
    __num_plants = 0
    __total_growth = 0

    def __init__(self, owner_name):
        """Initialize a garden with an owner's name."""
        self.set_onwer_name(owner_name)
        self.__plants = []

    def add_plant(self, plant):
        """Add a plant to the garden."""
        print(f"Added {plant.get_name()} to {self.get_owner_name()}'s garden")
        self.__num_plants += 1
        self.__plants.append(plant)

    def get_owner_name(self):
        """Return the name of the garden's owner."""
        return self.__onwer_name

    def get_num_plants(self):
        """Return the total number of plants in the garden."""
        return self.__num_plants

    def get_total_growth(self):
        """Return the total growth of all plants in the garden."""
        return self.__total_growth

    def set_onwer_name(self, onwer_name):
        """Set the owner's name of the garden."""
        self.__onwer_name = onwer_name

    def get_plants(self):
        """Return the list of plants in the garden."""
        return self.__plants

    def grow_plants(self, amount: int = 1):
        """Increase the growth of all plants in the garden."""
        print(f"{self.get_owner_name()} is helping all plants to grow...")
        for plant in self.get_plants():
            print(f"{plant.get_name()} grew {amount}cm")
            self.__total_growth += amount
            plant.grow(amount)

    def print_plants(self):
        """Print information about all the plants in the garden."""
        print("Plants in garden:")
        for plant in self.get_plants():
            print(plant.get_info())


class GardenManager:
    """A class to manage multiple gardens."""

    def __init__(self):
        """Initialize the garden manager."""
        self.__gardens = []

    def add_garden(self, garden):
        """Add a garden to the manager."""
        self.__gardens.append(garden)

    def print_garden(self, garden):
        """Print the information of a specific garden."""
        print(f"=== {garden.get_owner_name()}'s Garden Report ===")
        garden.print_plants()
        print()

    def get_gardens(self):
        """Return the list of gardens managed."""
        return self.__gardens

    @classmethod
    def create_garden_network(cls, gardens):
        """Create and return a garden
          manager initialized with given gardens."""
        manager = cls()
        for garden in gardens:
            manager.add_garden(garden)
        return manager

    class GardenStats:
        """A helper class for calculating garden statistics."""

        @staticmethod
        def count_plant_types(plants):
            """Count the number of regular, flowering,
              and prize plants in a garden."""
            regular = flowering = prize = 0
            for plant in plants.get_plants():
                if plant.get_type() == "regular":
                    regular += 1
                elif plant.get_type() == "flowering":
                    flowering += 1
                elif plant.get_type() == "prize":
                    prize += 1
            return regular, flowering, prize

        @staticmethod
        def show_stats(garden):
            """Display various statistics for a garden."""
            print(f"Plants added: {garden.get_num_plants()} " +
                  f", Total growth: {garden.get_total_growth()}cm")
            types = GardenManager.GardenStats.count_plant_types(garden)
            print(f"Plant types: {types[0]} regular, " +
                  f"{types[1]} flowering, {types[2]} prize flowers\n")

        @staticmethod
        def validate_heights(garden):
            """Validate that all plants in a
              garden have non-negative heights."""
            for plant in garden.get_plants():
                if plant.get_height() < 0:
                    return False
            return True

        @staticmethod
        def count_gardens(manager):
            """Count the total number of gardens managed."""
            num_gardens = 0
            for _ in manager.get_gardens():
                num_gardens += 1
            print(f"Total gardens managed: {num_gardens}\n")

        @staticmethod
        def calculate_scores(gardens):
            """Calculate scores for all gardens
              based on the number of plants and growth."""
            scores = {}
            for garden in gardens:
                num_plants = 0
                for _ in garden.get_plants():
                    num_plants += 1
                score = (num_plants * 10) + garden.get_total_growth()
                scores[garden.get_owner_name()] = score
            return scores

        @staticmethod
        def show_scores(gardens):
            """Display the scores for all gardens."""
            scores = GardenManager.GardenStats.calculate_scores(gardens)
            print("Garden Scores - ", end="")
            for owner, score in scores.items():
                print(f"{owner}: {score} ", end="")
            print()


def main():
    """Run the demonstration for the garden system."""
    manager = GardenManager()

    print("=== Garden Management System Demo ===\n")
    alice_garden = Garden("Alice")
    alice_garden.add_plant(Plant("Oak Tree", 100))
    alice_garden.add_plant(FloweringPlant("Rose", 25, "red"))
    alice_garden.add_plant(PrizeFlower("Sunflower", 50, "yellow", 10))
    print()
    alice_garden.grow_plants()
    print()

    bob_garden = Garden("Bob")
    bob_garden.add_plant(Plant("Maple Tree", 75))
    bob_garden.add_plant(FloweringPlant("Daisy", 15, "white"))
    print()
    bob_garden.grow_plants(2)
    print()

    manager = GardenManager.create_garden_network([alice_garden, bob_garden])
    manager.print_garden(alice_garden)

    GardenManager.GardenStats.show_stats(alice_garden)
    valid = GardenManager.GardenStats.validate_heights(alice_garden)
    if valid:
        print("Height validation test: True")
    else:
        print("Height validation test: False")
    GardenManager.GardenStats.show_scores(manager.get_gardens())
    GardenManager.GardenStats.count_gardens(manager)


if __name__ == "__main__":
    """Run the main function if this script is executed."""
    main()
