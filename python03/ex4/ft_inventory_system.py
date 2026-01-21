"""
ex4.ft_inventory_system
Learning how to use dictionaries
"""


def print_inventory(player_name, inventories):
    """Print one inventory of a player"""
    if not player_name or not inventories:
        print("Wrong params")
        return
    print(f"=== {player_name}'s Inventory ===")
    for item_name, item in inventories[player_name]["items"].items():
        print(f"{item_name} ({item['category']}, {item['rarity']}): ", end="")
        print(f"{item['amount']}x @ {item['price']} gold each = ", end="")
        print(f"{item['amount'] * item['price']} gold")
    print()


def count_items(player_name, inventories):
    """Count num of items of a player"""
    num_items = 0
    for _, item in inventories[player_name]["items"].items():
        num_items += item["amount"]
    return num_items


def count_gold(player_name, inventories):
    """Count gold of a player"""
    total_gold = 0
    for _, item in inventories[player_name]["items"].items():
        total_gold += item["amount"] * item["price"]
    return total_gold


def count_categories(player_name, inventories):
    """Count categories of items of a player"""
    categories = {}
    for _, item in inventories[player_name]["items"].items():
        category = item["category"]
        categories[category] = categories.get(category, 0) + item["amount"]
    return categories


def calculate_inventory_stats(player_name, inventories):
    """Calculate and show some stats"""
    if not player_name or not inventories:
        print("Wrong params")
        return
    print(f"Inventory value {count_gold(player_name, inventories)} gold")
    print(f"Item count {count_items(player_name, inventories)} items")
    categories = count_categories(player_name, inventories)
    print("Categories: ", end="")
    first = True
    for category, count in categories.items():
        if not first:
            print(", ", end="")
        print(f"{category}({count})", end="")
        first = False
    print("\n")


def transaction(player_name1, player_name2, inventories, item, amount):
    """Gives one object from player one to player 2
    if it exist and there is engouh amount"""
    print(f"=== Transaction: {player_name1}" +
          f" gives {player_name2} {amount} {item}s ===")
    if item not in inventories[player_name1]["items"]:
        print(f"{player_name1} doesnt have {item}.")
        return "Transaction failed"
    if inventories[player_name1]["items"][item]["amount"] < amount:
        print(f"{player_name1} doesnt have enough {item}.")
        return "Transaction failed"

    inventories[player_name1]["items"][item]["amount"] -= amount

    if item in inventories[player_name2]["items"]:
        inventories[player_name2]["items"][item]["amount"] += amount
    else:
        inventories[player_name2]["items"][item] = {
            **inventories[player_name1]["items"][item],
            "amount": amount
        }

    if inventories[player_name1]["items"][item]["amount"] == 0:
        inventories[player_name1]["items"].pop(item)
    return "Transaction successful!\n"


def get_item_info(name, inventories, item):
    """Print an item of a player"""
    if not name or not inventories or not item:
        print("No params")
        return
    if item in inventories[name]["items"]:
        print(f"{name} {item}s: {inventories[name]['items'][item]['amount']}")
    else:
        print(f"{name} {item}s: 0")


def get_most_valuable_player(inventories):
    """Player with most valuable inventory"""
    if not inventories:
        print("No players in inventory data.")
        return
    max_gold = 0
    gold = 0
    for player in inventories:
        gold = count_gold(player, inventories)
        if max_gold < gold:
            best_player = player
            max_gold = gold
    print(f"Most valuable player: {best_player} ({max_gold} gold)")


def get_most_items_player(inventories):
    """Player with most items"""
    if not inventories:
        print("No players in inventory data.")
        return
    max_items = 0
    items = 0
    for player in inventories:
        items = count_items(player, inventories)
        if max_items < items:
            best_player = player
            max_items = items
    print(f"Most items player: {best_player} ({max_items} items)")


def get_rarest_items_by_rarity(inventories):
    """Rarest existing items"""
    if not inventories:
        print("No players in inventory data.")
        return
    rarity_priority = ["legendary", "epic", "rare", "uncommon", "common"]
    rarity_items = {}

    for _, data in inventories.items():
        for item, details in data["items"].items():
            rarity = details["rarity"]
            if rarity not in rarity_items:
                rarity_items[rarity] = []
            rarity_items[rarity].append(item)

    for rarity in rarity_priority:
        if rarity in rarity_items:
            print(f"Rarest items:: {', '.join(rarity_items[rarity])}")
            return

    print("No items found for any defined rarity.")
