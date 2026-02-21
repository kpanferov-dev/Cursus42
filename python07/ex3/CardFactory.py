"""
CardFactory.py
Contains CardFactory abstract class
"""

from abc import ABC, abstractmethod
from typing import Dict, Union
from ex0.Card import Card


class CardFactory(ABC):
    """
    Abstract factory interface for creating themed cards
    """

    @abstractmethod
    def create_creature(self, name_or_power: Union[str, int]) -> Card:
        """
        Create a creature card

        Args:
            name_or_power: Either creature name or power level

        Returns:
            A creature card
        """
        pass

    @abstractmethod
    def create_spell(self, name_or_power: Union[str, int]) -> Card:
        """
        Create a spell card

        Args:
            name_or_power: Either spell name or power level

        Returns:
            A spell card
        """
        pass

    @abstractmethod
    def create_artifact(self, name_or_power: Union[str, int]) -> Card:
        """
        Create an artifact card

        Args:
            name_or_power: Either artifact name or power level

        Returns:
            An artifact card
        """
        pass

    @abstractmethod
    def create_themed_deck(self, size: int) -> Dict:
        """
        Create a themed deck of cards

        Args:
            size: Number of cards to create

        Returns:
            Dictionary with card types and lists of cards
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> Dict:
        """
        Get the supported card types and variants

        Returns:
            Dictionary with supported types
        """
        pass
