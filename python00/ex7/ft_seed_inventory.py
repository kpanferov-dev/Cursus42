def ft_seed_inventory(seed_type: str, quantity: int, unit: str) -> None:
    if unit == "packets":
        print(f"{seed_type.capitalize()} seeds: {quantity} {unit} available")
    elif unit == "grams":
        print(f"{seed_type.capitalize()} seeds: {quantity} {unit} total")
    elif unit == "area":
        print(f"{seed_type.capitalize()}", end="")
        print(f" seeds: covers {quantity} square meters")
    else:
        print("Unknown unit type")
