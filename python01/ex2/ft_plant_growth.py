#!/usr/bin/env python3

class Plant:
    def __init__(self, name: str, height: int, age_in_days: int):
        self.name = name
        self.height = height
        self.age_in_days = age_in_days

    def grow(self, growth_amount: int):
        self.height += growth_amount

    def age(self, age_increment: int):
        self.age_in_days += age_increment

    def get_info(self):
        print(f"{self.name}: {self.height}cm, {self.age_in_days} days old")


day = 1
growth_days = 6
p1 = Plant("Rose", 25, 30)
print(f"=== Day {day} ===")
p1.get_info()
day += growth_days
print(f"=== Day {day} ===")
p1.grow(growth_days)
p1.age(growth_days)
p1.get_info()
print(f"Growth this week: +{growth_days}cm")
