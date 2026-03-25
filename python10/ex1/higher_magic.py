"""
higher_magic.py
Playing with callables
"""


def spell_combiner(spell1: callable, spell2: callable) -> callable:
    """Combine 2 spells"""
    def combined(target):
        return (spell1(target), spell2(target))
    return combined


def power_amplifier(base_spell: callable, multiplier: int) -> callable:
    """Amplify spell power"""
    def amplified():
        return base_spell() * multiplier
    return amplified


def conditional_caster(condition: callable, spell: callable) -> callable:
    """If true then cast a spell"""
    def casted(target, a, b):
        if condition(a, b):
            return spell(target)
        return "Spell fizzled"
    return casted


def spell_sequence(spells: list[callable]) -> callable:
    """Cast spells in a sequence"""
    def sequence(target):
        return [spell(target) for spell in spells]
    return sequence


def fireball(target: str) -> str:
    return f"Fireball hits {target}"


def heal(target: str) -> str:
    return f"Heals {target}"


def damage() -> int:
    return 10


def condition(a: int, b: int) -> bool:
    return a > b


def main():
    """main"""
    test_targets = ['Dragon', 'Goblin', 'Wizard', 'Knight']

    print("\nTesting spell combiner...")

    combo_spell = spell_combiner(fireball, heal)
    result1, result2 = combo_spell(test_targets[0])
    print(f"Combined spell result: {result1}, {result2}")

    print("\nTesting power amplifier...")
    spell_amplified = power_amplifier(damage, 3)
    print(f"original: {damage()}, {spell_amplified()}")

    print("\nTesting conditional caster...")
    conditional_spell = conditional_caster(condition, fireball)
    print(conditional_spell(test_targets[1], 1, 2))

    print("\nTesting sequence...")
    spells = [
        lambda target: f"Iceball hits {target}",
        lambda target: f"Lightning hits {target}",
        lambda target: f"Frost hits {target}",
        lambda target: f"Shock hits {target}",
        lambda target: f"Burn hits {target}"
    ]
    sequence_spell = spell_sequence(spells)
    result = sequence_spell(test_targets[3])
    for spell in result:
        print(spell)


if __name__ == "__main__":
    main()
