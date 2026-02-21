"""
Combatable.py
Contains class Combatable
"""

from abc import ABC, abstractmethod
from typing import Dict


class Combatable(ABC):
    """
    Abstract interface for combat-capable entities
    """
    @abstractmethod
    def attack(self, target) -> Dict:
        """
        Attack a target

        Args:
            target: The target to attack

        Returns:
            Dictionary with attack results
        """
        pass

    @abstractmethod
    def defend(self, incoming_damage: int) -> Dict:
        """
        Defend against incoming damage

        Args:
            incoming_damage: Amount of damage to defend against

        Returns:
            Dictionary with defense results
        """
        pass

    @abstractmethod
    def get_combat_stats(self) -> Dict:
        """
        Get combat-related statistics

        Returns:
            Dictionary with combat stats
        """
        pass
