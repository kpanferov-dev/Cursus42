"""
constants.py
File that containts constants for config
"""

REQUIRED_KEYS = {
    "width",
    "height",
    "entry",
    "exit",
    "output_file",
    "perfect",
    "algorithm",
    "display",
    "seed",
}
ALGORITHMS = {"backtracking", "dfs", "prim", "kruskal"}
DISPLAYS = {"ascii", "graphic"}
POSITIVE_INT = {"width", "height", "seed"}
BOOL = {"perfect"}
TUPLES = {"entry", "exit"}

MAX_WIDTH = 30
MAX_HEIGHT = 30
