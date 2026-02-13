"""
spellbook.py: contains spells
"""


def record_spell(spell_name: str, ingredients: str) -> str:
    """If valid then record using late import"""
    from .validator import validate_ingredients

    validation_result = validate_ingredients(ingredients)
    if "VALID" in validation_result:
        return f"Spell recorded: {spell_name} ({validation_result})"
    else:
        return f"Spell rejected: {spell_name} ({validation_result})"
