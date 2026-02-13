"""
validator.py: validates spells
"""


def validate_ingredients(ingredients: str) -> str:
    """Check if all words are valid"""
    valid_elements = ["fire", "water", "earth", "air"]

    ing_list = [i.strip().lower() for i in ingredients.split(" ")]

    if all(i in valid_elements for i in ing_list):
        return f"{ingredients} - VALID"
    else:
        return f"{ingredients} - INVALID"
