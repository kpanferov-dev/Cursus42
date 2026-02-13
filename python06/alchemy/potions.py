"""
potions.py: contains alchemy recipes
"""


from .elements import create_fire, create_water
from alchemy.elements import create_air, create_earth


def healing_potion():
    return f"Healing potion brewed with {create_fire()} and {create_water()}"


def strength_potion():
    return f"Strength potion brewed with {create_earth()} and {create_fire()}"


def invisibility_potion():
    return (
            f"Invisibility potion brewed with {create_air()}" +
            f" and {create_water()}"
           )


def wisdom_potion():
    return (
            f"Wisdom potion brewed with all elements: {create_fire()}," +
            f"{create_water()}, {create_air()}, {create_earth()}"
           )
