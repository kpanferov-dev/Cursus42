"""
CreatureCard.py
File that contains CreatureCard Class
"""

from ex0.Card import Card
from typing import Dict


class CreatureCard(Card):
    """
    Represents a creature card in the game.
    A creature card has attributes such as
    attack and health, and can attack other
    creature cards, modifying their health.

    Attributes:
        name (str): The name of the creature card.
        cost (int): The cost to play the card.
        rarity (str): The rarity of the card.
        attack (int): The attack value of the creature.
        health (int): The health value of the creature.

    Methods:
        attack_target(target: CreatureCard) -> Dict:
            Attacks another creature card, reducing
            its health based on the attack value.

        get_card_info() -> Dict:
            Returns a dictionary with the creature's
            information (name, cost, rarity, attack, and health).

        set_health(health: int) -> None:
            Sets the health of the creature card,
            ensuring it's a positive integer.

        set_attack(attack: int) -> None:
            Sets the attack value of the creature card,
            ensuring it's a positive integer.
    """

    def __init__(self, name: str, cost: int,
                 rarity: str, attack: int, health: int) -> None:
        super().__init__(name, cost, rarity)
        self.type = "Creature"
        self.set_attack(attack)
        self.set_health(health)

    def attack_target(self, target: CreatureCard) -> Dict:
        """
        Attacks another creature card and updates its health.

        Args:
            target (CreatureCard): The target
            creature card to be attacked.

        Returns:
            dict: A dictionary with the result
            of the attack, including damage dealt
                  and whether the combat has
                  resolved (i.e., if the target is still alive).
        """
        if not isinstance(target, CreatureCard):
            raise TypeError("Target must be a CreatureCard instance.")

        rest_hp = target.health - self.attack
        health = 0 if rest_hp < 0 else rest_hp

        target.set_health(health)

        return {
            "attacker": self.name,
            "target": target.name,
            "damage_dealt": self.attack,
            "combat_resolved": target.health == 0
        }

    def play(self, game_state: Dict) -> Dict:
        """
        Plays the creature card in the game,
        checking if the player has enough mana.
        Updates the game state by adding the
        creature to the battlefield and deducting mana.

        Args:
            game_state (Dict): The current state of the game,
            including available mana and other details.

        Returns:
            dict: A dictionary with the result of the card play,
            including the card played, mana used, and the effect.
        """
        if not isinstance(game_state, dict):
            raise TypeError(f"game_state must be a dictionary, got {type(game_state).__name__}")

        required_keys = ['mana']
        missing_keys = [key for key in required_keys if key not in game_state]
        if missing_keys:
            raise ValueError(f"game_state missing required key(s): {missing_keys}")
        
        available_mana = game_state.get('mana', 0)
        if available_mana < 0:
            raise ValueError(f"Mana cannot be negative, got {available_mana}")

        if available_mana < self.cost:

            return {
                "card_played": None,
                "mana_used": 0,
                "effect": "Not enough mana to play the card"
            }

        game_state['mana'] -= self.cost

        return {
            "card_played": self.name,
            "mana_used": self.cost,
            "effect": "Creature summoned to battlefield"
        }

    def get_card_info(self) -> Dict:
        """
        Returns the information of the creature
        card, including basic info (from Card)
        and the creature-specific data (attack and health).

        Returns:
            dict: A dictionary containing the creature card's data.
        """
        card_info = super().get_card_info()
        card_info["type"] = self.type
        card_info["attack"] = self.attack
        card_info["health"] = self.health

        return card_info

    def set_health(self, health: int) -> None:
        """
        Sets the health of the creature card. It
        checks that health is a positive integer.

        Args:
            health (int): The new health value for the creature card.

        Raises:
            ValueError: If health is not a positive integer.
        """
        if health < 0 or not isinstance(health, int):
            raise ValueError("Health must be a positive integer.")
        self.health = health

    def set_attack(self, attack: int) -> None:
        """
        Sets the attack of the creature card. It
        checks that attack is a positive integer.

        Args:
            attack (int): The new attack value for the creature card.

        Raises:
            ValueError: If attack is not a positive integer.
        """
        if attack < 0 or not isinstance(attack, int):
            raise ValueError("Attack must be a positive integer.")
        self.attack = attack
