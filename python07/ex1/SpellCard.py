"""
SpellCard.py
Contains SpellCard class
"""

from typing import List, Dict
from ex0.Card import Card


class SpellCard(Card):
    """
    Represents a spell card in the game.

    A SpellCard is a type of Card that applies an effect (damage, heal,
    buff, or debuff) to one or more targets when played.
    """

    def __init__(self, name: str, cost: int, rarity: str,
                 effect_type: str) -> None:
        """
        Initialize a SpellCard instance.

        Args:
            name (str): The name of the spell card.
            cost (int): The mana cost required to play the card.
            rarity (str): The rarity level of the card.
            effect_type (str): The type of
            effect ("damage", "heal", "buff", "debuff").

        Raises:
            ValueError: If the effect_type is invalid.
        """
        super().__init__(name, cost, rarity)
        self.type = "Spell"
        self.set_effect(effect_type)
        self.effect_value = 3
        self.played = False

    def play(self, game_state: Dict) -> Dict:
        """
        Play the spell card if conditions are met.

        This method checks whether the spell has already been played,
        validates the game state, and ensures sufficient mana is available.

        Args:
            game_state (Dict): The current game state
            containing at least the 'mana' key.

        Returns:
            Dict: A dictionary describing the result of playing the card.
                  Includes card name, mana used, and effect information.

        Raises:
            TypeError: If game_state is not a dictionary.
            ValueError: If required keys are missing, mana is invalid,
                        or the spell has already been played.
        """
        if not game_state:
            raise ValueError("No game_state provided")
        if not isinstance(game_state, Dict):
            raise TypeError("game_state must be a " +
                            f"dictionary, got {type(game_state).__name__}")

        required_keys = ['mana']
        missing_keys = [key for key in required_keys if key not in game_state]
        if missing_keys:
            raise ValueError("game_state missing " +
                             f"required key(s): {missing_keys}")

        available_mana = game_state.get('mana', 0)
        if available_mana < 0:
            raise ValueError(f"Mana cannot be negative, got {available_mana}")

        if self.played:
            raise ValueError("Spell already played")

        if self.is_playable(available_mana):
            game_state['mana'] -= self.cost
            self.played = True

            return {
                "card_played": self.name,
                "mana_used": self.cost,
                "effect": self.effect_type
            }
        else:
            return {
                "card_played": None,
                "mana_used": 0,
                "effect": "Not enough mana to play the card"
            }

    def set_effect(self, effect: str) -> None:
        """
        Set the spell effect type.

        Args:
            effect (str): The effect type to assign.
                          Must be one of: "damage", "heal", "buff", "debuff".

        Raises:
            ValueError: If the effect is not a valid string or not supported.
        """
        if not effect:
            raise ValueError("No effect provided")
        effects = ["damage", "heal", "buff", "debuff"]
        if not isinstance(effect, str) or effect not in effects:
            raise ValueError("Invalid spell effect")
        self.effect_type = effect

    def resolve_effect(self, targets: List) -> Dict:
        """
        Apply the spell's effect to the given targets.

        Depending on the effect type, this method modifies the target's
        health or attack attributes.

        Args:
            targets (List): A list of target objects affected by the spell.
                            Each target must have health and/or attack
                            attributes with corresponding setter methods.

        Returns:
            Dict: A dictionary summarizing the spell resolution,
                  including spell name, effect type, targets, and result text.

        Raises:
            ValueError: If targets is not a list.
        """
        if not targets:
            raise ValueError("No game_state provided")
        if not isinstance(targets, List):
            raise ValueError("There is no target")

        effect_descriptions = {
            "damage": f"Deal {self.effect_value} damage to",
            "heal": f"Restored {self.effect_value} health to",
            "buff": f"Increased power by {self.effect_value} for",
            "debuff": f"Decreased power by {self.effect_value} for"
        }

        effect_desc = effect_descriptions.get(
            self.effect_type,
            f"Applied {self.effect_type} ({self.effect_value}) to"
        )

        for target in targets:
            if self.effect_type == "damage":
                diff = target.health - self.effect_value
                health = max(0, diff)
                target.set_health(health)

            elif self.effect_type == "heal":
                health = target.health + self.effect_value
                target.set_health(health)

            elif self.effect_type == "buff":
                attack = target.attack + self.effect_value
                target.set_attack(attack)

            elif self.effect_type == "debuff":
                diff = target.attack - self.effect_value
                attack = max(0, diff)
                target.set_attack(attack)

        return {
            "spell": self.name,
            "effect_type": self.effect_type,
            "targets": targets,
            "result": f"{effect_desc} {', '.join(targets)}"
        }
