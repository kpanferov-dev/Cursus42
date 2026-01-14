#!/usr/bin/env python3

class Plant:
    __type = "regular"

    def __init__(self, name: str, height: int):
        self.set_name(name)
        self.set_height(height)

    def get_name(self):
        return self.__name

    def get_height(self):
        return self.__height

    def get_type(self):
        return self.__type

    def set_name(self, name: str):
        self.__name = name

    def set_height(self, height: int):
        self.__height = height

    def grow(self, amount: int):
        self.__height += amount

    def get_info(self):
        return f"- {self.get_name()}: {self.get_height()}cm"


class FloweringPlant(Plant):
    __type = "flowering"

    def __init__(self, name: str, height: int, color: str, blooming=True):
        super().__init__(name, height)
        self.set_color(color)
        self.set_blooming(blooming)

    def get_color(self):
        return self.__color

    def get_blooming(self):
        if self.__blooming:
            return "blooming"
        else:
            return "not blooming"

    def get_type(self):
        return self.__type

    def set_color(self, color: str):
        self.__color = color

    def set_blooming(self, blooming: bool):
        self.__blooming = blooming

    def get_info(self):
        return (
                super().get_info() +
                f", {self.get_color()} flowers ({self.get_blooming()})"
        )


class PrizeFlower(FloweringPlant):
    __type = "prize"

    def __init__(self, name: str,
                 height: int,
                 color: str,
                 points: int,
                 blooming=True):
        super().__init__(name, height, color, blooming)
        self.set_points(points)

    def get_points(self):
        return self.__points

    def get_type(self):
        return self.__type

    def set_points(self, points):
        self.__points = points

    def get_info(self):
        return super().get_info() + f", Prize points: {self.get_points()}"


class Garden:
    __num_plants = 0
    __total_growth = 0

    def __init__(self, owner_name):
        self.set_onwer_name(owner_name)
        self.__plants = []

    def add_plant(self, plant):
        print(f"Added {plant.get_name()} to {self.get_owner_name()}'s garden")
        self.__num_plants += 1
        self.__plants.append(plant)

    def get_owner_name(self):
        return self.__onwer_name

    def get_num_plants(self):
        return self.__num_plants

    def get_total_growth(self):
        return self.__total_growth

    def set_onwer_name(self, onwer_name):
        self.__onwer_name = onwer_name

    def get_plants(self):
        return self.__plants

    def grow_plants(self, amount: int = 1):
        print(f"{self.get_owner_name()} is helping all plants to grow...")
        for plant in self.get_plants():
            print(f"{plant.get_name()} grew {amount}cm")
            self.__total_growth += amount
            plant.grow(amount)

    def print_plants(self):
        print("Plants in garden:")
        for plant in self.get_plants():
            print(plant.get_info())


class GardenManager():
    def __init__(self):
        self.__gardens = []

    def add_garden(self, garden):
        self.__gardens.append(garden)

    def print_garden(self, garden):
        print(f"=== {garden.get_owner_name()}'s Garden Report ===")
        garden.print_plants()
        print()

    def get_gardens(self):
        return self.__gardens

    @classmethod
    def create_garden_network(cls, gardens):
        manager = cls()
        for garden in gardens:
            manager.add_garden(garden)
        return manager

    class GardenStats():
        @staticmethod
        def count_plant_types(plants):
            regular = 0
            flowering = 0
            prize = 0
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
            print(f"Plants added: {garden.get_num_plants()} " +
                  f", Total growth: {garden.get_total_growth()}cm")
            types = GardenManager.GardenStats.count_plant_types(garden)
            print(f"Plant types: {types[0]} regular, " +
                  f"{types[1]} flowering, {types[2]} prize flowers\n")

        @staticmethod
        def validate_heights(garden):
            for plant in garden.get_plants():
                if plant.get_height() < 0:
                    return False
            return True

        @staticmethod
        def count_gardens(manager):
            num_gardens = 0
            for _ in manager.get_gardens():
                num_gardens += 1
            print(f"Total gardens managed: {num_gardens}\n")

        @staticmethod
        def calculate_scores(gardens):
            scores = {}
            for garden in gardens:
                score = (len(garden.get_plants()) * 10) + garden.get_total_growth()
                scores[garden.get_owner_name()] = score
            return scores

        @staticmethod
        def show_scores(gardens):
            scores = GardenManager.GardenStats.calculate_scores(gardens)
            print("Garden Scores - ", end="")
            for owner, score in scores.items():
                print(f"{owner}: {score} ", end="")
            print()


def main():
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
    main()
