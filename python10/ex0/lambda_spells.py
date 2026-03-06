"""
lambda_spells.py
Contains usefull functions
"""


def artifact_sorter(artifacts: list[dict]) -> list[dict]:
    """Sort by power"""
    return sorted(artifacts, key=lambda item: item['power'], reverse=True)


def power_filter(mages: list[dict], min_power: int) -> list[dict]:
    """Filter by min power"""
    return list(filter(lambda mage: mage['power'] >= min_power, mages))


def spell_transformer(spells: list[str]) -> list[str]:
    """Add prefix and sufix"""
    return list(map(lambda spell: '* ' + spell + ' *', spells))


def mage_stats(mages: list[dict]) -> dict:
    """Calculates average power rounded to 2 dec"""
    return {
            'max_power': max(mages, key=lambda mage: mage['power'])['power'],
            'min_power': min(mages, key=lambda mage: mage['power'])['power'],
            'avg_power': round(sum(map(lambda mage: mage['power'], mages)) /
                               len(mages), 2)
    }


def main():
    """main"""
    artifacts = [{'name': 'Fire Staff', 'power': 69, 'type': 'focus'},
                 {'name': 'Storm Crown', 'power': 89, 'type': 'weapon'},
                 {'name': 'Earth Shield', 'power': 73, 'type': 'accessory'},
                 {'name': 'Water Chalice', 'power': 78, 'type': 'armor'}]
    mages = [{'name': 'Zara', 'power': 66, 'element': 'ice'},
             {'name': 'Sage', 'power': 87, 'element': 'shadow'},
             {'name': 'Ash', 'power': 55, 'element': 'wind'},
             {'name': 'Riley', 'power': 51, 'element': 'earth'},
             {'name': 'Alex', 'power': 99, 'element': 'ice'}]
    spells = ['shield', 'flash', 'freeze', 'tornado']

    artifacts = artifact_sorter(artifacts)
    op_mages = power_filter(mages, 60)
    spells_format = spell_transformer(spells)
    stats = mage_stats(mages)

    print("Testing artifact sorter...")
    for artifact in artifacts:
        print(f"{artifact['name']} - Power: {artifact['power']}")

    print("\nTesting power filter")
    for mage in op_mages:
        print(f"{mage['name']} - Power: {mage['power']}")

    print("\nTesting spell transformer...")
    for spell in spells_format:
        print(spell, end=" ")

    print("\n\nTesting stats")
    print(f"{stats}")


if __name__ == "__main__":
    main()
