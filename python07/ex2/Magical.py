"""
Magical.py
Contains Magical class
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class Magical(ABC):
    """
    Abstract interface for magic-capable entities
    """

    @abstractmethod
    def cast_spell(self, spell_name: str, targets: List) -> Dict:
        """
        Cast a spell on targets

        Args:
            spell_name: Name of the spell to cast
            targets: List of target identifiers

        Returns:
            Dictionary with spell casting results
        """
        pass

    @abstractmethod
    def channel_mana(self, amount: int) -> Dict:
        """
        Channel mana to increase magical power

        Args:
            amount: Amount of mana to channel

        Returns:
            Dictionary with channeling results
        """
        pass

    @abstractmethod
    def get_magic_stats(self) -> Dict:
        """
        Get magic-related statistics

        Returns:
            Dictionary with magic stats
        """
        pass
