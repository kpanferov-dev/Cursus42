"""
scope_mysteries.py
Playing with closures
"""
def mage_counter() -> callable:
    """counter with static count"""
    count = 0

    def counter():
        nonlocal count
        count += 1
        return count
    return counter


def spell_accumulator(initial_power: int) -> callable:
    """counter with initial value"""
    power = initial_power

    def accumulate(add_power):
        nonlocal power
        power += add_power
        return power
    return accumulate


def enchantment_factory(enchantment_type: str) -> callable:
    """Add en enchantment string leading the item"""
    def enchant(item):
        return f"{enchantment_type} {item}"
    return enchant


def memory_vault() -> dict[str, callable]:
    """Return a dict with 'store' and 'recall' closure functions."""
    vault = {}
    def store(key, value):
        vault[key] = value
    def recall(key):
        return vault.get(key, "Memory not found")
    return {"store": store, "recall": recall}


def main():
    """main"""

    print("\nTesting mage counter...")
    my_counter = mage_counter()
    for i in range(1, 4):
        print(f"Call: {i}: {my_counter()}")

    print("\nTesting spell accumulator...")
    power = spell_accumulator(5)
    for i in range(1, 4):
        print(f"Call: {i}: {power(10)}")

    print("\nTesting  enchantment factory...")
    enchant = enchantment_factory("Enchanted")
    flaming = enchantment_factory("Flaming")
    ice = enchantment_factory("Icy")

    print(enchant("Sword"))
    print(flaming("Shield"))
    print(ice("Dagger"))

    print("Testing memory vault...")
    vault = memory_vault()
    vault["store"]("hero", "Merlin")
    vault["store"]("level", 99)

    print(vault["recall"]("hero"))
    print(vault["recall"]("level"))


if __name__ == "__main__":
    main()
