#!/usr/bin/env python3

class SecurePlant:
    def __init__(self, name: str, height: int, age: int):
        if height < 0 or age < 0:
            print("Invalid plant values")
            self.__valid = False
            return
        self.__name = name
        self.__valid = True
        print(f"Plant created: {self.__name}")
        self.set_height(height)
        self.set_age(age)

    def get_height(self):
        return self.__height

    def get_age(self):
        return self.__age

    def set_height(self, height: int):
        if height < 0:
            print(f"Invalid operation attempted: height {height}cm [REJECTED]")
        else:
            if self.__valid:
                print(f"Height updated: {height}cm [OK]")
                self.__height = height

    def set_age(self, age: int):
        if age < 0:
            print("Security: Negative age rejected")
        else:
            if self.__valid:
                print(f"Age updated: {age} days [OK]")
                self.__age = age

    def get_info(self):
        if self.__valid:
            content = f"({self.get_height()}cm, {self.get_age()} days)"
            return f"Current plant: {self.__name} " + content
        else:
            return "Plant doesn´t exist"


print("=== Garden Security System ===")
plant = SecurePlant("Rose", 25, 30)
print()
plant.set_height(-5)
plant.set_age(-50)
print()
print(plant.get_info())
