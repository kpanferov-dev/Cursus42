class Plant:
    def __init__(self, name, height):
        self.name = name
        self.height = height

    def grow(self, growth=1):
        self.height += growth
        print(f"{self.name} grew {growth}cm")

    def describe(self):
        return f"{self.name}: {self.height}cm"

    def get_type(self):
        return "regular"


class FloweringPlant(Plant):
    def __init__(self, name, height, flower_color, blooming=False):
        super().__init__(name, height)
        self.flower_color = flower_color
        self.blooming = blooming

    def bloom(self):
        self.blooming = True
        print(f"{self.name} is now blooming with {self.flower_color} flowers")

    def describe(self):
        blooming_state = "blooming" if self.blooming else "not blooming"
        return f"{self.name}: {self.height}cm, {self.flower_color} flowers ({blooming_state})"

    def get_type(self):
        return "flowering"


class PrizeFlower(FloweringPlant):
    def __init__(self, name, height, flower_color, prize_points, blooming=False):
        super().__init__(name, height, flower_color, blooming)
        self.prize_points = prize_points

    def describe(self):
        blooming_state = "blooming" if self.blooming else "not blooming"
        return (f"{self.name}: {self.height}cm, {self.flower_color} flowers ({blooming_state}), "
                f"Prize points: {self.prize_points}")

    def get_type(self):
        return "prize"


class GardenManager:
    class GardenStats:
        @staticmethod
        def calculate_total_growth(plants):
            return sum(plant.height for plant in plants)

        @staticmethod
        def count_plant_types(plants):
            regular = sum(1 for plant in plants if plant.get_type() == "regular")
            flowering = sum(1 for plant in plants if plant.get_type() == "flowering")
            prize = sum(1 for plant in plants if plant.get_type() == "prize")
            return regular, flowering, prize

    def __init__(self):
        self.gardens = {}

    def create_garden(self, owner_name):
        self.gardens[owner_name] = []

    def add_plant(self, owner_name, plant):
        if owner_name not in self.gardens:
            print(f"Garden for {owner_name} does not exist. Creating one...")
            self.create_garden(owner_name)
        self.gardens[owner_name].append(plant)
        print(f"Added {plant.name} to {owner_name}'s garden")

    def list_gardens(self):
        for owner, plants in self.gardens.items():
            print(f"=== {owner}'s Garden Report ===")
            print("Plants in garden:")
            for plant in plants:
                print(f"- {plant.describe()}")
            total_growth = self.GardenStats.calculate_total_growth(plants)
            types = self.GardenStats.count_plant_types(plants)
            print(f"Plants added: {len(plants)}, Total growth: {total_growth}cm")
            print(f"Plant types: {types[0]} regular, {types[1]} flowering, {types[2]} prize flowers")

    @classmethod
    def create_garden_network(cls):
        print("Creating a garden network... This is a class-level operation.")

    @staticmethod
    def validate_garden_structure():
        print("Static method called: Garden structure validated.")


if __name__ == "__main__":
    manager = GardenManager()

    print("=== Garden Management System Demo ===")
    manager.create_garden("Alice")

    oak_tree = Plant("Oak Tree", 100)
    rose = FloweringPlant("Rose", 25, "red", blooming=True)
    sunflower = PrizeFlower("Sunflower", 50, "yellow", 10, blooming=True)

    manager.add_plant("Alice", oak_tree)
    manager.add_plant("Alice", rose)
    manager.add_plant("Alice", sunflower)

    print("Alice is helping all plants grow...")
    for plant in manager.gardens["Alice"]:
        plant.grow()

    manager.list_gardens()

    GardenManager.create_garden_network()
    GardenManager.validate_garden_structure()