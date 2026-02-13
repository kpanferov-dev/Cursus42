"""
ft_sacred_scroll: main program part1
"""

import alchemy

print("=== Sacred Scroll Mastery ===\n")

print("Testing direct module access:")
for func_name in ["create_fire", "create_water", "create_earth", "create_air"]:
    func = getattr(alchemy.elements, func_name)
    print(f"alchemy.elements.{func_name}(): {func()}")

print("\nTesting package-level access (controlled by __init__.py):")
for func_name in ["create_fire", "create_water", "create_earth", "create_air"]:
    try:
        func = getattr(alchemy, func_name)
        print(f"alchemy.{func_name}(): {func()}")
    except AttributeError:
        print(f"alchemy.{func_name}(): AttributeError - not exposed")

print("\nPackage metadata:")
print(f"Version: {alchemy.__version__}")
print(f"Author: {alchemy.__author__}")
