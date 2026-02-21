"""
Demonstration script for the Game Engine with Strategy and Factory Patterns
"""

from .FantasyCardFactory import FantasyCardFactory
from .AggressiveStrategy import AggressiveStrategy
from .GameEngine import GameEngine


def main() -> None:
    """Main demonstration function"""

    print("=== DataDeck Game Engine ===\n")

    try:
        # Create factory and strategy
        factory = FantasyCardFactory()
        strategy = AggressiveStrategy()

        # Create and configure engine
        engine = GameEngine()

        print("Configuring Fantasy Card Game...")
        engine.configure_engine(factory, strategy)

        # Show available types
        supported_types = factory.get_supported_types()
        print(f"Available types: {supported_types}")

        # Show initial hand
        print("\nSimulating aggressive turn...")
        print(f"Hand: {engine.get_hand_display()}")

        # Simulate a turn
        turn_result = engine.simulate_turn()

        # Display turn execution
        print("\nTurn execution:")
        print(f"Strategy: {turn_result['strategy']}")
        print(f"Actions: {turn_result['actions']}")

        # Display game report
        print("\nGame Report:")
        status = engine.get_engine_status()
        print(status)

        print("\nAbstract Factory + Strategy " +
              "Pattern: Maximum flexibility achieved!")

    except ValueError as e:
        print(f"\n Value Error: {e}")
    except TypeError as e:
        print(f"\n Type Error: {e}")
    except Exception as e:
        print(f"\n Unexpected Error: {e}")


if __name__ == "__main__":
    main()
