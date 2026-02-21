"""
ArtifactCard.py
Contains ArtifactCard class
"""
from typing import Dict
from ex0.Card import Card


class ArtifactCard(Card):
    """Represent an artifact card with durability
    and an activatable ability."""

    def __init__(
        self,
        name: str,
        cost: int,
        rarity: str,
        durability: int,
        effect: str,
    ) -> None:
        """Initialize an ArtifactCard instance.

        Args:
            name (str): Name of the artifact card.
            cost (int): Mana cost required to play the card.
            rarity (str): Rarity level of the card.
            durability (int): Number of times the artifact can be used.
            effect (str): Description of the artifact's ability.
        """
        super().__init__(name, cost, rarity)
        self.type = "Artifact"
        self.durability = durability
        self.effect = effect
        self.in_play = False

    def play(self, game_state: Dict) -> Dict:
        """Play the artifact card if sufficient mana is available.

        Validate the game state, ensure the artifact is not already in
        play, and deduct mana if the card can be played.

        Args:
            game_state (Dict): Current game state containing at least the
                'mana' key.

        Returns:
            Dict: Result of the play attempt including card name, mana
                used, and effect description.

        Raises:
            TypeError: If game_state is not a dictionary.
            ValueError: If required keys are missing, mana is invalid,
                or the artifact is already in play.
        """
        if not game_state:
            raise ValueError("No game_state provided")
        if not isinstance(game_state, Dict):
            raise TypeError(
                "game_state must be a "
                + f"dictionary, got {type(game_state).__name__}"
            )

        required_keys = ["mana"]
        missing_keys = [
            key for key in required_keys if key not in game_state
        ]
        if missing_keys:
            raise ValueError(
                "game_state missing "
                + f"required key(s): {missing_keys}"
            )

        available_mana = game_state.get("mana", 0)
        if available_mana < 0:
            raise ValueError(
                f"Mana cannot be negative, got {available_mana}"
            )

        if self.in_play:
            raise ValueError("Artifact already played")

        if self.is_playable(available_mana):
            game_state["mana"] -= self.cost
            self.in_play = True

            return {
                "card_played": self.name,
                "mana_used": self.cost,
                "effect": self.effect,
            }

        return {
            "card_played": None,
            "mana_used": 0,
            "effect": "Not enough mana to play the card",
        }

    def activate_ability(self) -> Dict:
        """Activate the artifact ability and reduce durability by one.

        Decrease durability each time the ability is used. If durability
        reaches zero, mark the artifact as destroyed and remove it from
        play.

        Returns:
            Dict: Dictionary containing activation results, remaining
                durability, and destruction status.

        Raises:
            ValueError: If the artifact is not in play or already
                destroyed.
        """
        if not self.in_play:
            raise ValueError("Artifact not in play")

        if self.durability <= 0:
            raise ValueError("Artifact destroyed")

        self.durability -= 1

        result = {
            "artifact": self.name,
            "ability_activated": self.effect,
            "durability_remaining": self.durability,
            "destroyed": self.durability <= 0,
        }

        if self.durability <= 0:
            self.in_play = False
            result["destroyed"] = True

        return result
