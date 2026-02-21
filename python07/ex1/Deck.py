"""
Deck.py
Contains Deck class
"""
from typing import List, Dict
import random
from ex0.Card import Card
from ex0.CreatureCard import CreatureCard
from .SpellCard import SpellCard
from .ArtifactCard import ArtifactCard


class Deck:
    """Represent a deck of cards."""

    def __init__(self, name: str = "Unnamed Deck") -> None:
        """Initialize a Deck instance.

        Args:
            name (str): Name of the deck. Defaults to "Unnamed Deck".
        """
        self.name = name
        self.cards: List[Card] = []

    def add_card(self, card: Card) -> None:
        """Add a card to the deck.

        Args:
            card (Card): Card instance to add.

        Raises:
            ValueError: If the object is not a Card.
        """
        if not card:
            raise ValueError("No card provided")
        if not isinstance(card, Card):
            raise ValueError("Not a card")
        self.cards.append(card)

    def remove_card(self, card_name: str) -> bool:
        """Remove a card from the deck by name.

        Args:
            card_name (str): Name of the card to remove.

        Returns:
            bool: True if the card was removed, False otherwise.

        Raises:
            ValueError: If card_name is not a string.
        """
        if not card_name:
            raise ValueError("No card_name provided")
        if not isinstance(card_name, str):
            raise ValueError("Not a card name")
        for i, card in enumerate(self.cards):
            if card.name == card_name:
                self.cards.pop(i)
                return True
        return False

    def shuffle(self) -> None:
        """Shuffle the deck randomly.

        Raises:
            ValueError: If the deck is empty.
        """
        if not self.cards:
            raise ValueError("Empty deck")
        random.shuffle(self.cards)

    def draw_card(self) -> Card:
        """Draw (remove and return) the top card from the deck.

        Returns:
            Card: The card drawn from the deck.

        Raises:
            ValueError: If the deck is empty.
        """
        if not self.cards:
            raise ValueError("Empty deck")
        return self.cards.pop(0)

    def get_deck_stats(self) -> Dict:
        """Calculate and return statistics about the deck.

        Returns:
            Dict: Dictionary containing total cards, number of creatures,
                spells, artifacts, and average cost.

        Raises:
            ValueError: If the deck is empty or contains unknown card types.
        """
        if not self.cards:
            raise ValueError("Empty deck")

        total_cards = len(self.cards)
        creatures = 0
        spells = 0
        artifacts = 0
        total_cost = 0

        for card in self.cards:
            total_cost += card.cost

            if isinstance(card, SpellCard):
                spells += 1
            elif isinstance(card, ArtifactCard):
                artifacts += 1
            elif isinstance(card, CreatureCard):
                creatures += 1
            else:
                raise ValueError("Not identified card")

        avg_cost = total_cost / total_cards

        return {
            "total_cards": total_cards,
            "creatures": creatures,
            "spells": spells,
            "artifacts": artifacts,
            "avg_cost": round(avg_cost, 1),
        }
