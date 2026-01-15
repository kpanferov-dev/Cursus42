#!/usr/bin/env python3
"""
ft_garden_management.py
Mix of the previous
"""


class GardenError(Exception):
    """General Errors"""
    def __init__(self, message="General error"):
        super().__init__(message)


class PlantError(GardenError):
    """Plant Errors"""
    def __init__(self, message="The tomato plant is wilting!"):
        super().__init__(message)


class WaterError(GardenError):
    """Water Errors"""
    def __init__(self, message="Not enough water in tank"):
        super().__init__(message)


class GardenManager:
    """Garden Manager ......."""
    def __init__(self):
        self.plants = {}
        self.water_available = 20

    def add_plant(self, name, water_level, sunlight_hours):
        """Function that adds and object"""
        try:
            if name.strip() == "" or name is None:
                raise PlantError("Plant name cannot be empty!")
            if water_level < 1:
                raise PlantError(f"Water level {water_level}" +
                                 " is too low (min 1)\n")
            elif water_level > 10:
                raise PlantError(f"Water level {water_level}" +
                                 " is too high (max 10)\n")
            if sunlight_hours < 2:
                raise PlantError(f"Sunlight hours {sunlight_hours}" +
                                 " is too low (min 2)\n")
            elif sunlight_hours > 12:
                raise PlantError("Sunlight hours " +
                                 f"{sunlight_hours}" +
                                 " is too high (max 12)\n")
            self.plants[name] = {"water_level": water_level,
                                 "sunlight_hours": sunlight_hours}
            print(f"Added {name} successfully")
        except PlantError as e:
            print(f"Error adding plant: {e}")

    def water_plants(self):
        """Water plants by spending water from tank"""
        print("Opening watering system")
        try:
            for name, info in self.plants.items():
                try:
                    if self.water_available < info["water_level"]:
                        raise WaterError
                    self.water_available -= info["water_level"]
                    print(f"Watering {name} - success")
                except WaterError as e:
                    print(f"Error watering {name}: {e}")
        finally:
            print("Closing watering system (cleanup)\n")

    def check_plant_health(self):
        """Check plants health"""
        print("Checking plant health...")
        for name, info in self.plants.items():
            try:
                water_level = info["water_level"]
                sunlight_hours = info["sunlight_hours"]

                if water_level < 1:
                    raise PlantError(f"Water level {water_level}" +
                                     " is too low (min 1)\n")
                elif water_level > 10:
                    raise PlantError(f"Water level {water_level}" +
                                     " is too high (max 10)\n")
                if sunlight_hours < 2:
                    raise PlantError(f"Sunlight hours {sunlight_hours}" +
                                     " is too low (min 2)\n")
                elif sunlight_hours > 12:
                    raise PlantError("Sunlight hours" +
                                     f"{sunlight_hours}" +
                                     " is too high (max 12)\n")
                print(f"{name}: healthy (water: {water_level}" +
                      f", sun: {sunlight_hours})")
            except PlantError as e:
                print(f"Error checking {name}: {e}")


def test_garden_manager():
    """main program for testing functionality"""
    print("=== Garden Management System ===\n")
    garden = GardenManager()

    print("Adding plants to garden...")
    garden.add_plant("tomato", 5, 8)
    garden.add_plant("lettuce", 10, 6)
    garden.add_plant("", 4, 5)

    print("\nWatering plants...")
    garden.water_plants()

    garden.check_plant_health()

    print("\nTesting error recovery...")
    try:
        if garden.water_available < 20:
            raise WaterError
    except GardenError as e:
        print(f"Caught GardenError: {e}")
    finally:
        print("System recovered and continuing...\n")

    print("Garden management system test complete!")


test_garden_manager()
