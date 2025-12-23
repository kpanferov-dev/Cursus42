#!/usr/bin/env python3

class Plant:
    def __init__(self, name: str, height: int):
        self.__name = name
        self.__height = height

    def get_name(self):
        return self.__name

    def get_height(self):
        return self.__height

    def grow(self, amount: int):
        self.__height += amount

    def get_info(self):
        return f"{self.get_name()}: {self.get_height()}cm"


class FloweringPlant(Plant):
    def __init__(self, name: str, height: int, color: str, blooming: bool):
        super().__init__(name, height)
        self.__color = color
        self.__blooming = blooming

    def get_color(self):
        return self.__color

    def bloom(self):
        self.__blooming = True

    def get_blooming(self):
        return self.__blooming

    def is_blooming(self):
        return "blooming" if self.__blooming else "not blooming"

    def get_info(self):
        bloom_st = self.is_blooming() + ")"
        return super().get_info() + f", {self.get_color()} flowers ({bloom_st}"


class PrizeFlower(FloweringPlant):
    def __init__(self, name: str, height: int, flower_color: str, pr_pts: int):
        super().__init__(name, height, flower_color)
        self.pr_pts = pr_pts

    def get_info(self):
        base_info = super().get_info()
        return f"{base_info}, Prize points: {self.pr_pts}"


class Garden:
    def __init__(self, owner: str):
        self.owner = owner
        self.plants = []
        self.score = 0

    def add_plant(self, plant):
        self.plants.append(plant)
        print(f"Added {plant.name} to {self.owner}'s garden")

    def grow_plants(self):
        for plant in self.plants:
            plant.grow(1)
            print(f"{plant.name} grew 1cm")


class GardenStats:
    def __init__(self, garden):
        self.garden = garden

    def total_growth(self):
        return sum(plant.height for plant in self.garden.plants)

    def plant_count(self):
        return len(self.garden.plants)

    def plant_types(self):
        types = {"regular": 0, "flowering": 0, "prize_flower": 0}
        for plant in self.garden.plants:
            if isinstance(plant, PrizeFlower):
                types["prize_flower"] += 1
            elif isinstance(plant, FloweringPlant):
                types["flowering"] += 1
            else:
                types["regular"] += 1
        return types

    def height_validation(self):
        return all(plant.height >= 0 for plant in self.garden.plants)

    def report(self):
        total_growth = self.total_growth()
        plant_count = self.plant_count()
        plant_types = self.plant_types()
        height_validation = self.height_validation()

        print(f"=== {self.garden.owner}'s Garden Report ===")
        print("Plants in garden:")
        for plant in self.garden.plants:
            print(f"- {plant.get_info()}")
        print(f"Plants added: {plant_count}, Total growth: {total_growth}cm")
        content1 = f"Plant types: {plant_types['regular']}"
        content2 = f" regular, {plant_types['flowering']}"
        content3 = f" flowering, {plant_types['prize_flower']} prize flowers"
        print(f"{content1}{content2}{content3}")
        print(f"Height validation test: {height_validation}")
        print(f"Garden scores - {self.garden.owner}: {self.garden.score}")


class GardenManager:
    total_gardens = 0

    def __init__(self):
        self.gardens = []

    @classmethod
    def create_garden_network(cls):
        garden1 = Garden("Alice")
        garden2 = Garden("Bob")
        cls.total_gardens += 2
        return [garden1, garden2]

    @classmethod
    def get_total_gardens(cls):
        return cls.total_gardens

    @staticmethod
    def report_all_gardens(self):
        for garden in self.gardens:
            stats = GardenStats(garden)
            stats.report()


manager = GardenManager()
gardens = manager.create_garden_network()
manager.gardens.extend(gardens)
oak_tree = Plant("Oak Tree", 100)
rose = FloweringPlant("Rose", 25, "red",False)
sunflower = PrizeFlower("Sunflower", 50, "yellow", 10)
gardens[0].add_plant(oak_tree)
gardens[0].add_plant(rose)
gardens[0].add_plant(sunflower)
gardens[0].grow_plants()
manager.report_all_gardens()
print(f"Is Rose flowering? {Plant.is_flowering(rose)}")
print(f"Total gardens managed: {GardenManager.get_total_gardens()}")
