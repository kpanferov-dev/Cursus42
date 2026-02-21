"""
ex2 __init__.py - Makes the ex2 repository a Python package
This allows importing  Combatable.py, Magical.py, EliteCard.py
"""

from .Combatable import Combatable
from .Magical import Magical
from .EliteCard import EliteCard

__all__ = ["Combatable", "Magical", "EliteCard"]
