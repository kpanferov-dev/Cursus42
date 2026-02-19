#!/usr/bin/env python3
"""
Demonstration script for the Card Foundation
Tests the abstract base class design
"""

from ex0.CreatureCard import CreatureCard

def main():
    """Main demonstration function"""
    
    print("\n=== DataDeck Card Foundation ===\n")
    print("Testing Abstract Base Class Design:\n")
    
    game_state = {
        "mana": 6,
        "battlefield": []
    }

    try:
        creature1 = CreatureCard('Fire Dragon', 5, 'Legendary', 7, 5)
        creature2 = CreatureCard('Goblin Warrior', 3, 'Legendary', 1, 2)
    except Exception as e:
        print(f"Failed to create cards: {e}")
        return

    try:
        print("\nCreatureCard Info")
        print(creature1.get_card_info())
    except Exception as e:
        print(f"Error getting card info: {e}")
    
    try:
        print(f"\nPlaying {creature1.name} with" +
              f" {game_state['mana']} mana available:")
        print(f"Playable: {creature1.is_playable(game_state['mana'])}")
        result = creature1.play(game_state)
        print(f"Play result: {result}")
    except Exception as e:
        print(f"Error playing card: {e}")
    
    try:
        print(f"\n{creature1.name} attacks {creature2.name}")
        result = creature1.attack_target(creature2)
        print(f"Attack result: {result}")
    except Exception as e:
        print(f"Error during attack: {e}")
    
    try:
        game_state["mana"] = 3
        print(f"\nTesting insufficient mana ({game_state['mana']} available):")
        print(f"Playable: {creature1.is_playable(game_state['mana'])}")
    except Exception as e:
        print(f"Error checking mana: {e}")
    
    print()
    print("Abstract pattern successfully demonstrated!")

if __name__ == "__main__":
    main()