"""
Rankable.py
Contains Rankable abstract class
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class Rankable(ABC):
    """
    Abstract interface for rankable entities in a tournament
    """

    @abstractmethod
    def calculate_rating(self) -> int:
        """
        Calculate the current rating based on wins and losses

        Returns:
            int: Calculated rating
        """
        pass

    @abstractmethod
    def update_wins(self, wins: int) -> None:
        """
        Update the win count

        Args:
            wins: Number of wins to add
        """
        pass

    @abstractmethod
    def update_losses(self, losses: int) -> None:
        """
        Update the loss count

        Args:
            losses: Number of losses to add
        """
        pass

    @abstractmethod
    def get_rank_info(self) -> Dict[str, Any]:
        """
        Get ranking information

        Returns:
            Dictionary with rank info (rating, wins, losses)
        """
        pass
