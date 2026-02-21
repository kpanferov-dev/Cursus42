#!/usr/bin/env python3
"""
Demonstration script for the Tournament Platform
"""

from .TournamentCard import TournamentCard
from .TournamentPlatform import TournamentPlatform


def main() -> None:
    """Main demonstration function"""

    print("=== DataDeck Tournament Platform ===\n")

    try:
        # Create tournament platform
        platform = TournamentPlatform("DataDeck Championship")

        # Create tournament cards
        print("Registering Tournament Cards...")

        dragon = TournamentCard(
            name="Fire Dragon",
            cost=5,
            rarity="Epic",
            attack=6,
            health=5,
            card_id="dragon_001"
        )

        wizard = TournamentCard(
            name="Ice Wizard",
            cost=4,
            rarity="Rare",
            attack=4,
            health=4,
            card_id="wizard_001"
        )
        wizard.initial_rating = wizard.rating = 1150

        # Register cards
        platform.register_card(dragon)
        platform.register_card(wizard)

        # Create a tournament match
        print("\nCreating tournament match...")
        match_result = platform.create_match("dragon_001", "wizard_001")
        print(f"Match result: {match_result}")

        # Show leaderboard
        print("\nTournament Leaderboard:")
        leaderboard = platform.get_leaderboard()
        for entry in leaderboard:
            print(f"{entry['rank']}. {entry['name']} - "
                  f"Rating: {entry['rating']} ({entry['record']})")

        # Generate tournament report
        print("\nPlatform Report:")
        report = platform.generate_tournament_report()
        print(report)

        print("\n=== Tournament Platform Successfully Deployed! ===")
        print("All abstract patterns working together harmoniously!")

    except ValueError as e:
        print(f"\n Value Error: {e}")
    except TypeError as e:
        print(f"\n Type Error: {e}")
    except Exception as e:
        print(f"\n Unexpected Error: {e}")


if __name__ == "__main__":
    main()
