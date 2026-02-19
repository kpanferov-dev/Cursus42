"""
Card.py
File that containts Card class
"""
from abc import ABC, abstractmethod
from typing import Dict


class Card(ABC):
    """
    Abstract base class representing a card in a game.
    Classes that inherit from this class must
      implement the `play` method to define
    the specific behavior of the card when played.

    Attributes:
        name (str): The name of the card.
        cost (int): The mana cost of the card.
        rarity (str): The rarity of the card.
    """

    def __init__(self, name: str, cost: int, rarity: str) -> None:
        """
        Initializes a new card instance.

        Args:
            name (str): The name of the card.
            cost (int): The mana cost of the card.
            rarity (str): The rarity of the card.
        """
        self.name = name
        self.cost = cost
        self.rarity = rarity

    @abstractmethod
    def play(self, game_state: Dict) -> Dict:
        """
        Abstract method to be implemented by subclasses.

        This method defines the logic for the card
          when played. It should modify the game state
        based on the card's effect.

        Args:
            game_state (Dict): The current state of the
              game, which should be modified by the card.

        Returns:
            Dict: The updated game state after playing the card.
        """
        pass

    def is_playable(self, available_mana: int) -> bool:
        """
        Determines if the card can be played based on the available mana.

        If the available mana is enough to play the card, it returns `True`.
        Otherwise, it returns `False`.

        Args:
            available_mana (int): The available mana to play the card.

        Raises:
            ValueError: If `available_mana` is not a positive integer.

        Returns:
            bool: `True` if the card can be played, `False` if it cannot.
        """
        if not isinstance(available_mana, int) or available_mana < 0:
            raise ValueError("Must be a positive integer")
        return available_mana >= self.cost

    def get_card_info(self) -> Dict:
        """
        Returns a dictionary with the basic information of the card.

        This includes the name, mana cost, and rarity of the card.

        Returns:
            Dict: A dictionary containing the card's data.
        """
        return {"name": self.name, "cost": self.cost, "rarity": self.rarity}
