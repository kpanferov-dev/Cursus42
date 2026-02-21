"""
GameStrategy.py
Contains abstract class GameStrategy
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class GameStrategy(ABC):
    """
    Abstract strategy interface for game AI behavior
    """

    @abstractmethod
    def execute_turn(self, hand: List, battlefield: List) -> Dict:
        """
        Execute a turn based on the current game state

        Args:
            hand: List of cards in hand
            battlefield: List of cards on the battlefield

        Returns:
            Dictionary with turn execution results
        """
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """
        Get the name of the strategy

        Returns:
            Strategy name as string
        """
        pass

    @abstractmethod
    def prioritize_targets(self, available_targets: List) -> List:
        """
        Prioritize targets for attacks

        Args:
            available_targets: List of possible targets

        Returns:
            Prioritized list of targets
        """
        pass
