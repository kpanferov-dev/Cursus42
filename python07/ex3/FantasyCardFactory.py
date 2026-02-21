"""
FantasyCard.py
Contains FantasyCard class
"""
from typing import Dict, List, Union
import random
from ex0.Card import Card
from ex0.CreatureCard import CreatureCard
from ex1.SpellCard import SpellCard
from ex1.ArtifactCard import ArtifactCard


class FantasyCardFactory:
    """
    Concrete factory that creates fantasy-themed cards
    """

    def __init__(self):
        """Initialize the fantasy card factory with available types"""
        self.factory_name = "FantasyCardFactory"

        # Define available card types
        self.creature_types = {
            "dragon": {"name": "Fire Dragon", "cost": 5,
                       "rarity": "Epic", "attack": 6, "health": 5},
            "goblin": {"name": "Goblin Warrior", "cost": 2,
                       "rarity": "Common", "attack": 2, "health": 1}
            }

        self.spell_types = {
            "fireball": {"name": "Fire Ball", "cost": 3,
                         "rarity": "Common", "effect_type": "damage",
                         "effect_value": 3},
            "lightning": {"name": "Lightning Bolt", "cost": 3,
                          "rarity": "Rare", "effect_type": "damage",
                          "effect_value": 6},
        }

        self.artifact_types = {
            "mana_ring": {"name": "Mana Ring", "cost": 2,
                          "rarity": "Rare", "durability": 3,
                          "effect": "+1 mana per turn"}
        }

    def create_creature(self, name_or_power: Union[str, int]) -> CreatureCard:
        """
        Create a fantasy creature card

        Args:
            name_or_power: Either creature name (str) or power level (int)

        Returns:
            A CreatureCard instance
        """
        if not name_or_power:
            raise ValueError("Not valid name or power")
        if isinstance(name_or_power, int):
            # Scale creature based on power level
            power = min(10, max(1, name_or_power))
            return CreatureCard(
                f"Fantasy Creature {power}",
                cost=power,
                rarity=("Common" if power <= 3
                        else "Rare" if power <= 6 else "Epic"),
                attack=power,
                health=power
            )
        else:
            # Create specific creature by name
            creature_name = name_or_power.lower()
            if creature_name not in self.creature_types:
                # Default to goblin if not found
                creature_name = "goblin"

            stats = self.creature_types[creature_name]
            return CreatureCard(
                name=stats["name"],
                cost=stats["cost"],
                rarity=stats["rarity"],
                attack=stats["attack"],
                health=stats["health"]
            )

    def create_spell(self, name_or_power: Union[str, int]) -> SpellCard:
        """
        Create a fantasy spell card

        IMPORTANTE: Adaptado para tu SpellCard
        que NO tiene effect_value en __init__

        Args:
            name_or_power: Either spell name (str) or power level (int)

        Returns:
            A SpellCard instance
        """
        if isinstance(name_or_power, int):
            # Scale spell based on power level
            power = min(10, max(1, name_or_power))
            effects = ["damage", "heal", "buff", "debuff"]
            effect_type = effects[0]

            spell = SpellCard(
                f"Fantasy Spell {power}",
                cost=power,
                rarity=("Common" if power <= 3
                        else "Rare" if power <= 6 else "Epic"),
                effect_type=effect_type
            )
            spell.effect_value = power
            return spell
        else:
            # Create spell by name
            spell_name = name_or_power.lower()
            if spell_name not in self.spell_types:
                spell_name = "fireball"

            stats = self.spell_types[spell_name]

            spell = SpellCard(
                name=stats["name"],
                cost=stats["cost"],
                rarity=stats["rarity"],
                effect_type=stats["effect_type"],
            )
            spell.effect_value = stats["effect_value"]
            return spell

    def create_artifact(self, name_or_power: Union[str, int]) -> ArtifactCard:
        """
        Create a fantasy artifact card

        Args:
            name_or_power: Either artifact name (str) or power level (int)

        Returns:
            An ArtifactCard instance
        """
        if isinstance(name_or_power, int):
            # Scale artifact based on power level
            power = min(10, max(1, name_or_power))
            return ArtifactCard(
                f"Fantasy Artifact {power}",
                cost=power,
                rarity=("Common" if power <= 3
                        else "Rare" if power <= 6 else "Epic"),
                durability=power,
                effect=f"Magical effect level {power}"
            )
        else:
            # Create specific artifact by name
            artifact_name = name_or_power.lower()
            if artifact_name not in self.artifact_types:
                artifact_name = "mana_ring"

            stats = self.artifact_types[artifact_name]
            return ArtifactCard(
                name=stats["name"],
                cost=stats["cost"],
                rarity=stats["rarity"],
                durability=stats["durability"],
                effect=stats["effect"]
            )

    def create_themed_deck(self, size: int) -> Dict[str, List[Card]]:
        """
        Create a themed deck of fantasy cards

        Args:
            size: Number of cards to create

        Returns:
            Dictionary with card types and lists of cards
        """
        if size <= 0:
            raise ValueError("Deck size must be positive")

        deck = {
            "creatures": [],
            "spells": [],
            "artifacts": []
        }

        # Distribute cards roughly: 60% creatures, 30% spells, 10% artifacts
        num_creatures = int(size * 0.6)
        num_spells = int(size * 0.3)
        num_artifacts = size - num_creatures - num_spells

        # Create creatures
        creature_names = list(self.creature_types.keys())
        for _ in range(num_creatures):
            name = random.choice(creature_names)
            deck["creatures"].append(self.create_creature(name))

        # Create spells
        spell_names = list(self.spell_types.keys())
        for _ in range(num_spells):
            name = random.choice(spell_names)
            deck["spells"].append(self.create_spell(name))

        # Create artifacts
        artifact_names = list(self.artifact_types.keys())
        for _ in range(num_artifacts):
            name = random.choice(artifact_names)
            deck["artifacts"].append(self.create_artifact(name))

        return deck

    def get_supported_types(self) -> Dict[str, List[str]]:
        """
        Get the supported card types and variants

        Returns:
            Dictionary with supported types
        """
        return {
            "creatures": list(self.creature_types.keys()),
            "spells": list(self.spell_types.keys()),
            "artifacts": list(self.artifact_types.keys())
        }
