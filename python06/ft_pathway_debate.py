"""
ft_pathway_debate: main program for part3
"""


import alchemy
from alchemy.transmutation.basic import lead_to_gold
from alchemy.transmutation.advanced import philosophers_stone, elixir_of_life


print("=== Pathway Debate Mastery ===\n")

print("Testing Absolute Imports (from basic.py):")
print(f"lead_to_gold(): {alchemy.transmutation.basic.lead_to_gold()}")
print(f"stone_to_gem(): {alchemy.transmutation.basic.stone_to_gem()}\n")

print("Testing Relative Imports (from advanced.py):")
print(f"philosophers_stone(): {philosophers_stone()}")
print(f"elixir_of_life(): {elixir_of_life()}\n")

print("Testing Package Access:")
print("alchemy.transmutation.lead_to_gold():" +
      f" {lead_to_gold()}")
print("alchemy.transmutation.philosophers_stone():" +
      f" {philosophers_stone()}\n")

print("Both pathways work! Absolute: clear, Relative: concise")
