"""
ft_circular_curse: main for part4
"""


from alchemy.grimoire import record_spell, validate_ingredients

print("=== Circular Curse Breaking ===\n")

print("Testing ingredient validation:")
ing1 = "fire air"
ing2 = "dragon scales"
print(f'validate_ingredients("{ing1}"): {validate_ingredients(ing1)}')
print(f'validate_ingredients("{ing2}"): {validate_ingredients(ing2)}\n')

print("Testing spell recording with validation:")
spell1 = ("Fireball", "fire air")
spell2 = ("Dark Magic", "shadow")
print(f'record_spell("{spell1[0]}", "{spell1[1]}"): {record_spell(*spell1)}')
print(f'record_spell("{spell2[0]}", "{spell2[1]}"): {record_spell(*spell2)}\n')

print("Testing late import technique:")
spell3 = ("Lightning", "air")
print(f'record_spell("{spell3[0]}", "{spell3[1]}"): {record_spell(*spell3)}\n')

print("Circular dependency curse avoided using late imports!")
print("All spells processed safely!")
