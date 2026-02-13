"""
advanced.py: advanced alchemy
"""


from .basic import lead_to_gold
from ..potions import healing_potion


def philosophers_stone():
    """Create a stone"""
    return (
            "Philosopher’s stone created using " +
            f"{lead_to_gold()} and {healing_potion()}"
            )


def elixir_of_life():
    """Create an elixir"""
    return "Elixir of life: eternal youth achieved!"
