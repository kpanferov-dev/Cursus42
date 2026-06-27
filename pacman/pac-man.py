#!/usr/bin/env python3
"""Pac-Man - entry point.

Usage::

    python3 pac-man.py config.json

The single mandatory argument is a JSON (with comments) configuration file.
Any error is reported with a clear message; the program never shows a raw
Python traceback to the user.
"""
from __future__ import annotations

import sys

from src.config_loader import load_config
from src.game import Game


def main(argv: list[str]) -> int:
    """Parse arguments, load the config and launch the game.

    Args:
        argv: The full ``sys.argv`` list.

    Returns:
        A process exit code (0 on success, non-zero on a usage error).
    """
    if len(argv) != 2:
        print("Usage: python3 pac-man.py <config.json>")
        return 1
    path = argv[1]
    if not path.lower().endswith(".json"):
        print("Error: the configuration file must be a .json file.")
        return 1

    config = load_config(path)
    try:
        Game(config).run()
    except Exception as error:  # last-resort guard: never crash on the user
        print(f"Fatal error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
