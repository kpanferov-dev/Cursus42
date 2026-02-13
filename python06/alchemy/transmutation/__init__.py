"""
__init__.py: manage directory transmutation as a package
"""

__version__ = "1.0.0"
__author__ = "Master Pythonicus"

from .basic import lead_to_gold, stone_to_gem
from .advanced import philosophers_stone, elixir_of_life

__all__ = ["lead_to_gold", "stone_to_gem",
           "philosophers_stone", "elixir_of_life"]
