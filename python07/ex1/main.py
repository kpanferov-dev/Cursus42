"""
main.py
Main file of ex1
"""

from ex0.CreatureCard import CreatureCard
from .SpellCard import SpellCard
from .ArtifactCard import ArtifactCard
from .Deck import Deck


def main() -> None:
    print("\n=== DataDeck Deck Builder ===\n")
    print("Building deck with different card types...")
    try:
        deck = Deck("My awesome deck")
        game_state = {"mana": 60,
                      "battlefield": []}

        spell = SpellCard("Lightning Bolt", 3, "Common", "damage")
        artifact = ArtifactCard("Mana Crystal",
                                2, "Rare", 5, "+1 mana per turn")
        creature = CreatureCard("Fire Dragon", 5, "Epic", 6, 5)

        deck.add_card(spell)
        deck.add_card(artifact)
        deck.add_card(creature)

        stats = deck.get_deck_stats()
        print("\nDeck stats:", stats)

        print("\nDrawing and playing cards:")

        for card in range(len(deck.cards)):
            card = deck.draw_card()
            print(f"\nDrew: {card.name} ({card.type})")
            if card:
                result = card.play(game_state)
                print(f"Play result: {result}")
    except Exception as e:
        print(f"Error: {e}")
    print("\nPolymorphism in action: Same " +
          "interface, different card behaviors!")


if __name__ == "__main__":
    main()
