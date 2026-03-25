#!/usr/bin/env python3
"""
Demonstration script for the Ability System with Multiple Interfaces
"""

from ex0.CreatureCard import CreatureCard
from .EliteCard import EliteCard


def main() -> None:
    """Main demonstration function"""

    print("=== DataDeck Ability System ===\n")

    try:
        arcane_warrior = EliteCard(
            "Arcane Warrior",
            5,           # cost
            "Legendary",  # rarity
            5,           # attack
            8,           # health
            8            # mana
        )

        print("EliteCard capabilities:")
        info = arcane_warrior.get_card_info()
        combat_info = arcane_warrior.get_combat_stats()
        magic_info = arcane_warrior.get_magic_stats()
        print(f"-{info['stats_type']} : {info['card']}")
        print(f"-{combat_info['stats_type']} : {combat_info['combatable']}")
        print(f"-{magic_info['stats_type']} : {magic_info['magical']}")

        enemy = CreatureCard("Enemy", 0, "Common", 3, 5)

        print(f"\nPlaying {arcane_warrior.name} (Elite Card):")
        game_state = {"mana": 10,
                      "battlefield": []}
        arcane_warrior.play(game_state)

        print("\nCombat phase:")
        print(f"Attack result: {arcane_warrior.attack(enemy)}")

        defend_result = arcane_warrior.defend(5)
        print(f"Defense result: {defend_result}")

        print("\nMagic phase:")

        enemy1 = CreatureCard("Enemy1", 0, "Common", 2, 3)
        enemy2 = CreatureCard("Enemy2", 0, "Common", 2, 3)

        print("Spell cast: " +
              f"{arcane_warrior.cast_spell('fireball', [enemy1, enemy2])}")

        channel_result = arcane_warrior.channel_mana(3)
        print(f"Mana channel: {channel_result}")

        print("\nMultiple interface implementation successful!")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
