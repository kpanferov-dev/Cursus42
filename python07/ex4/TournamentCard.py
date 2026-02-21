from typing import Dict, Any
from ex0.Card import Card
from ex2.Combatable import Combatable
from .Rankable import Rankable


class TournamentCard(Card, Combatable, Rankable):
    """
    Enhanced card that combines Card, Combatable, and Rankable interfaces
    for tournament participation
    """

    def __init__(self, name: str, cost: int, rarity: str,
                 attack: int, health: int, card_id: str = ""):
        """
        Initialize a Tournament Card

        Args:
            name: Card name
            cost: Mana cost
            rarity: Card rarity
            attack: Base attack power
            health: Base health
            card_id: Unique identifier (auto-generated if not provided)
        """
        super().__init__(name, cost, rarity)

        # Combat attributes
        self.attack_power = attack
        self.health = health
        self.max_health = health
        self.defense = attack // 2

        # Tournament attributes
        self.card_id = card_id
        self.wins = 0
        self.losses = 0
        self.rating = 1200
        self.initial_rating = 1200
        self.matches_played = 0

        # State
        self.type = "Tournament"
        self.in_play = False

    # ===== Card Implementation =====
    def play(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Play the tournament card
        """
        if not isinstance(game_state, dict):
            raise TypeError("game_state must be a dictionary")

        if 'mana' not in game_state:
            raise ValueError("game_state missing 'mana' key")

        available_mana = game_state['mana']

        if not self.is_playable(available_mana):
            return {
                "card_played": None,
                "mana_used": 0,
                "effect": "Not enough mana to play the card"
            }

        if self.in_play:
            return {
                "card_played": None,
                "mana_used": 0,
                "effect": "Card already in play"
            }

        game_state['mana'] -= self.cost
        self.in_play = True

        if 'battlefield' in game_state:
            game_state['battlefield'].append(self)

        return {
            "card_played": self.name,
            "mana_used": self.cost,
            "effect": "Tournament card summoned to battlefield",
            "card_id": self.card_id
        }

    def get_card_info(self) -> Dict[str, Any]:
        """Get complete card information"""
        info = super().get_card_info()
        info.update({
            "type": self.type,
            "attack": self.attack_power,
            "health": self.health,
            "max_health": self.max_health,
            "defense": self.defense,
            "card_id": self.card_id,
            "in_play": self.in_play
        })
        return info

    # ===== Combatable Implementation =====
    def attack(self, target) -> Dict[str, Any]:
        """
        Perform a melee attack on a target.

        Args:
            target (Any): Target object with health and set_health().

        Returns:
            Dict: Dictionary containing attack result information.
        """
        if not target:
            raise ValueError("No targets provided")
        rest_hp = target.health - self.attack_power
        health = 0 if rest_hp < 0 else rest_hp
        target.set_health(health)

        return {
            "attacker": self.name,
            "target": target.name,
            "damage": self.attack_power,
            "combat_type": "melee",
        }

    def defend(self, incoming_damage: int) -> Dict[str, Any]:
        """
        Defend against incoming damage.

        Args:
            incoming_damage (int): Amount of damage received.

        Returns:
            Dict: Dictionary describing damage taken and status.

        Raises:
            ValueError: If incoming_damage is invalid.
        """
        if incoming_damage is None:
            raise ValueError("No damage provided")
        if not isinstance(incoming_damage, int) or incoming_damage <= 0:
            raise ValueError("Invalid incoming damage")

        damage = incoming_damage - self.defense
        damage_blocked = (
            self.defense
            if self.defense < incoming_damage
            else incoming_damage
        )
        true_damage = max(0, damage)

        rest_hp = self.health - true_damage
        health = 0 if rest_hp < 0 else rest_hp
        self.set_health(health)

        return {
            "defender": self.name,
            "damage_taken": true_damage,
            "damage_blocked": damage_blocked,
            "still_alive": health > 0,
        }

    def get_combat_stats(self) -> Dict[str, Any]:
        """Get combat statistics"""
        return {
            "attack": self.attack_power,
            "health": self.health,
            "max_health": self.max_health,
            "defense": self.defense
        }

    # ===== Rankable Implementation =====
    def calculate_rating(self) -> int:
        """
        Calculate Elo-like rating based on performance

        Simplified Elo: base + (wins * 16) - (losses * 16)
        """
        self.rating = (self.initial_rating +
                       (self.wins * 16) - (self.losses * 16))
        return self.rating

    def update_wins(self, wins: int = 1) -> None:
        """Update win count and recalculate rating"""
        if wins < 0:
            raise ValueError("Wins cannot be negative")
        self.wins += wins
        self.matches_played += wins
        self.calculate_rating()

    def update_losses(self, losses: int = 1) -> None:
        """Update loss count and recalculate rating"""
        if losses < 0:
            raise ValueError("Losses cannot be negative")
        self.losses += losses
        self.matches_played += losses
        self.calculate_rating()

    def get_rank_info(self) -> Dict[str, Any]:
        """Get ranking information"""
        return {
            "card_id": self.card_id,
            "name": self.name,
            "rating": self.rating,
            "wins": self.wins,
            "losses": self.losses,
            "matches_played": self.matches_played,
        }

    # ===== Tournament Methods =====
    def get_tournament_stats(self) -> Dict[str, Any]:
        """Get complete tournament statistics"""
        return {
            "card_info": self.get_card_info(),
            "combat_stats": self.get_combat_stats(),
            "rank_info": self.get_rank_info(),
            "interfaces": ["Card", "Combatable", "Rankable"]
        }

    def set_health(self, health: int) -> None:
        """
        Sets the health of the creature card. It
        checks that health is a positive integer.

        Args:
            health (int): The new health value for the creature card.

        Raises:
            ValueError: If health is not a positive integer.
        """
        if health is None or health < 0 or not isinstance(health, int):
            raise ValueError("Health must be a positive integer.")
        self.health = health
