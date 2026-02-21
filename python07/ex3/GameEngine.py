"""
GameEngine.py
Contains GameEngine Class
"""
from typing import Dict, Any, List, Optional
from ex0.Card import Card
from ex0.CreatureCard import CreatureCard
from ex1.Deck import Deck
from .CardFactory import CardFactory
from .GameStrategy import GameStrategy


class GameEngine:
    """
    Game orchestrator that uses factory and strategy patterns
    """

    def __init__(self):
        """Initialize the game engine"""
        self.factory: Optional[CardFactory] = None
        self.strategy: Optional[GameStrategy] = None
        self.deck: Optional[Deck] = None
        self.hand: List[Card] = []
        self.battlefield: List[CreatureCard] = []
        self.turns_simulated = 0
        self.total_damage = 0
        self.cards_created = 0

    def configure_engine(self, factory: CardFactory,
                         strategy: GameStrategy) -> None:
        """
        Configure the engine with a factory and strategy
        """
        self.factory = factory
        self.strategy = strategy

        self.deck = Deck("Game Deck")
        themed_cards = self.factory.create_themed_deck(3)

        for cards in themed_cards.values():
            for card in cards:
                self.deck.add_card(card)
                self.cards_created += 1

        self.deck.shuffle()

        self.hand = [
            self.factory.create_creature("dragon"),
            self.factory.create_creature("goblin"),
            self.factory.create_spell("lightning")
        ]

    def simulate_turn(self) -> Dict[str, Any]:
        """
        Simulate a turn using the configured strategy
        """
        self.turns_simulated += 1

        turn_result = self.strategy.execute_turn(self.hand, self.battlefield)

        self.total_damage += turn_result.get("damage_dealt", 0)

        cards_played = turn_result.get("cards_played", [])
        self.hand = [c for c in self.hand if c.name not in cards_played]

        for _ in range(len(cards_played)):
            try:
                self.hand.append(self.deck.draw_card())
            except ValueError:
                import random
                card = self.factory.create_creature(random.randint(1, 3))
                self.hand.append(card)
                self.cards_created += 1

        return {
            "strategy": self.strategy.get_strategy_name(),
            "actions": turn_result
        }

    def get_engine_status(self) -> Dict[str, Any]:
        """
        Get the current engine status
        """
        return {
            "turns_simulated": self.turns_simulated,
            "strategy_used": (self.strategy.get_strategy_name()
                              if self.strategy else "None"),
            "total_damage": self.total_damage,
            "cards_created": self.cards_created,
        }

    def get_hand_display(self) -> List[str]:
        """Get display names of cards in hand"""
        return [f"{c.name} ({c.cost})" for c in self.hand]
