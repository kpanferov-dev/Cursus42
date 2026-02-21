from typing import List, Dict, Any
from ex0.Card import Card
from ex0.CreatureCard import CreatureCard
from ex1.SpellCard import SpellCard
from .GameStrategy import GameStrategy


class AggressiveStrategy(GameStrategy):
    """
    Concrete strategy that prioritizes attacking and dealing damage
    """

    def __init__(self):
        """Initialize the aggressive strategy"""
        self.strategy_name = "AggressiveStrategy"
        self.mana_available = 5

    def execute_turn(self, hand: List[Card],
                     battlefield: List[CreatureCard]) -> Dict[str, Any]:
        """
        Execute an aggressive turn:
        - Play low-cost creatures first
        - Attack with all available creatures
        - Use spells for direct damage

        USA EL MÉTODO play() DE CADA CARTA
        """
        if not isinstance(hand, list):
            raise ValueError("Hand must be a list")
        if not isinstance(battlefield, list):
            raise ValueError("Battlefield must be a list")

        cards_played = []
        mana_used = 0
        damage_dealt = 0
        targets_attacked = []

        game_state = {
            "mana": self.mana_available,
            "battlefield": battlefield
        }

        sorted_hand = sorted(hand, key=lambda c: c.cost)

        for card in sorted_hand:
            if card.cost <= game_state["mana"]:
                play_result = card.play(game_state)

                if play_result.get("card_played"):
                    cards_played.append(card.name)
                    mana_used += card.cost

                if (isinstance(card, SpellCard) and
                   card.effect_type == "damage"):
                    damage_dealt += card.effect_value
                    targets_attacked.append("Enemy Player")

        self.mana_available = game_state["mana"]

        for creature in battlefield:
            if isinstance(creature, CreatureCard):
                damage_dealt += creature.attack
                targets_attacked.append("Enemy Player")

        return {
            "cards_played": cards_played,
            "mana_used": mana_used,
            "targets_attacked": list(set(targets_attacked)),
            "damage_dealt": damage_dealt,
        }

    def get_strategy_name(self) -> str:
        """Get the name of this strategy"""
        return self.strategy_name

    def prioritize_targets(self, available_targets: List) -> List:
        """
        Prioritize targets for aggressive strategy
        """
        if not available_targets:
            return []

        def target_priority(target):
            if hasattr(target, 'is_player') and target.is_player:
                return 0
            elif isinstance(target, CreatureCard):
                if target.health <= 3:
                    return 1
                elif target.attack >= 5:
                    return 2
                return 3
            return 4

        return sorted(available_targets, key=target_priority)
