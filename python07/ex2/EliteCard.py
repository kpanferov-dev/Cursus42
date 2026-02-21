"""
EliteCard.py
Contains EliteCard Class implementation
"""

from typing import Dict, Any, List
from ex0.Card import Card
from .Combatable import Combatable
from .Magical import Magical


class EliteCard(Card, Combatable, Magical):
    """
    Elite card that combines combat and magical abilities.

    This class uses multiple inheritance to provide both
    combat and magic behaviors.
    """

    def __init__(
        self,
        name: str,
        cost: int,
        rarity: str,
        attack: int,
        health: int,
        mana: int,
    ) -> None:
        """
        Initialize an EliteCard instance.

        Args:
            name (str): Card name.
            cost (int): Mana cost required to play the card.
            rarity (str): Card rarity.
            attack (int): Base attack power.
            health (int): Base health value.
            mana (int): Base mana pool.
        """
        super().__init__(name, cost, rarity)
        self.type = "Elite"
        self.set_attack(attack)
        self.set_health(health)
        self.set_mana(mana)
        self.defense = attack // 2

    def attack(self, target: Any) -> Dict:
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

    def defend(self, incoming_damage: int) -> Dict:
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

    def play(self, game_state: Dict) -> Dict:
        """
        Play the card if enough mana is available.

        Args:
            game_state (Dict): Current game state containing 'mana'.

        Returns:
            Dict: Dictionary describing the play result.

        Raises:
            TypeError: If game_state is not a dictionary.
            ValueError: If required keys are missing or invalid.
        """
        if not game_state:
            raise ValueError("No game_state provided")
        if not isinstance(game_state, dict):
            raise TypeError(
                f"game_state must be dict, got "
                f"{type(game_state).__name__}"
            )

        required_keys = ["mana"]
        missing_keys = [
            key for key in required_keys if key not in game_state
        ]
        if missing_keys:
            raise ValueError(
                f"game_state missing required key(s): {missing_keys}"
            )

        available_mana = game_state.get("mana", 0)
        if available_mana < 0:
            raise ValueError(
                f"Mana cannot be negative, got {available_mana}"
            )

        if self.is_playable(available_mana):
            game_state["mana"] -= self.cost
            return {
                "card_played": self.name,
                "mana_used": self.cost,
                "effect": "Creature summoned to battlefield",
            }

        return {
            "card_played": None,
            "mana_used": 0,
            "effect": "Not enough mana to play the card",
        }

    def get_card_info(self) -> Dict:
        """
        Return full card information.

        Returns:
            Dict: Dictionary containing base and elite attributes.
        """
        card_info = super().get_card_info()
        card_info["type"] = self.type
        card_info["attack"] = self.attack_power
        card_info["health"] = self.health
        card_info["defense"] = self.defense
        card_info["mana"] = self.mana
        card_info["stats_type"] = "Card"
        card_info["card"] = [
            "play",
            "get_card_info",
            "is_playable",
        ]
        return card_info

    def get_combat_stats(self) -> Dict:
        """
        Return combat-related statistics.

        Returns:
            Dict: Dictionary with attack and defense values.
        """
        return {
            "attack": self.attack_power,
            "defense": self.defense,
            "stats_type": "Combatable",
            "combatable": [
                "attack",
                "defend",
                "get_combat_stats",
            ],
        }

    def set_health(self, health: int) -> None:
        """
        Set the health value.

        Args:
            health (int): New health value.

        Raises:
            ValueError: If health is negative or not an integer.
        """
        if health is None:
            raise ValueError("No health provided")
        if health < 0 or not isinstance(health, int):
            raise ValueError("Health must be a positive integer.")
        self.health = health

    def set_attack(self, attack: int) -> None:
        """
        Set the attack value.

        Args:
            attack (int): New attack value.

        Raises:
            ValueError: If attack is negative or not an integer.
        """
        if attack is None:
            raise ValueError("No attack provided")
        if attack < 0 or not isinstance(attack, int):
            raise ValueError("Attack must be a positive integer.")
        self.attack_power = attack

    def set_mana(self, mana: int) -> None:
        """
        Set the mana value.

        Args:
            mana (int): New mana value.

        Raises:
            ValueError: If mana is negative or not an integer.
        """
        if mana is None:
            raise ValueError("No mana provided")
        if mana < 0 or not isinstance(mana, int):
            raise ValueError("Mana must be a positive integer.")
        self.mana = mana

    def cast_spell(self, spell_name: str, targets: List) -> Dict:
        """
        Cast a spell on one or more targets.

        Args:
            spell_name (str): Name of the spell.
            targets (List): List of target objects.

        Returns:
            Dict: Dictionary describing spell result.

        Raises:
            ValueError: If inputs are invalid or mana is insufficient.
        """
        spells = ["fireball", "fire storm", "ice blast"]
        if not spell_name:
            raise ValueError("No spell name provided")
        if not targets:
            raise ValueError("No targets provided")
        if not isinstance(targets, list):
            raise ValueError("There is no target")

        if not isinstance(spell_name, str):
            raise ValueError("There is no spell")

        if spell_name not in spells:
            raise ValueError("Spell does not exist")

        if self.mana < 4:
            raise ValueError("Not enough mana")
        targets_format = []
        for target in targets:
            diff = target.health - 2
            health = max(0, diff)
            target.set_health(health)
            targets_format.append(target.name.capitalize())

        self.set_mana(self.mana - 4)

        return {
            "caster": self.name,
            "spell": spell_name.capitalize(),
            "targets": targets_format,
            "mana_used": 4,
        }

    def channel_mana(self, amount: int) -> Dict:
        """
        Increase the card's mana pool.

        Args:
            amount (int): Mana amount to add.

        Returns:
            Dict: Dictionary with updated mana information.

        Raises:
            ValueError: If amount is invalid.
        """
        if amount is None:
            raise ValueError("No amount provided")
        if not isinstance(amount, int) or amount <= 0:
            raise ValueError("Invalid mana amount, min 1")

        self.set_mana(self.mana + amount)

        return {
            "channeled": amount,
            "total_mana": self.mana,
        }

    def get_magic_stats(self) -> Dict:
        """
        Return magic-related statistics.

        Returns:
            Dict: Dictionary with mana and magical abilities.
        """
        return {
            "mana": self.mana,
            "stats_type": "Magical",
            "magical": [
                "cast_spell",
                "channel_mana",
                "get_magic_stats",
            ],
        }
