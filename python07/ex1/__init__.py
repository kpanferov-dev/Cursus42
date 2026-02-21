"""
ex1 __init__.py - Makes the ex1 repository a Python package
This allows importing SpellCard ArtifactCard Deck
"""

from .SpellCard import SpellCard
from .ArtifactCard import ArtifactCard
from .Deck import Deck

__all__ = ["SpellCard", "ArtifactCard", "Deck"]
