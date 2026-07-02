#!/usr/bin/env python3
"""Pac-Man - entry point.

Usage::

    python3 pac-man.py config.json

The single mandatory argument is a JSON (with comments) configuration file.
Any error is reported with a clear message; the program never shows a raw
Python traceback to the user.

When the program is run as a **packaged build** (PyInstaller, e.g. the Itch.io
release), it is started by a double-click with no argument, so it falls back
to the ``config.json`` bundled next to the executable.  Launched as a plain
script it always requires exactly one argument, as the subject mandates.
"""
from __future__ import annotations

import os
import sys

# Keep the usage/error output clean: silence pygame's import banner before the
# game module (which imports pygame) is loaded.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from src.config_loader import load_config  # noqa: E402
from src.game import Game  # noqa: E402

DEFAULT_CONFIG = "config.json"


def _frozen() -> bool:
    """True when running from a PyInstaller-frozen executable."""
    return bool(getattr(sys, "frozen", False))


def _bundled_config() -> str:
    """Path to the config shipped inside the frozen build (or the cwd one)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    candidate = os.path.join(base, DEFAULT_CONFIG)
    return candidate if os.path.isfile(candidate) else DEFAULT_CONFIG


def _resolve_config_path(argv: list[str]) -> str | None:
    """Return the config path to use, or ``None`` on a usage error.

    Args:
        argv: The full ``sys.argv`` list.

    Returns:
        A path to a ``.json`` config file, or ``None`` if the command-line
        usage was invalid (a message has already been printed in that case).
    """
    if _frozen():
        # Packaged build: optional path argument, default to the bundled one.
        if len(argv) >= 2 and argv[1].lower().endswith(".json"):
            return argv[1]
        return _bundled_config()

    # Plain script: exactly one .json argument is required (subject V.1).
    if len(argv) != 2:
        print("Usage: python3 pac-man.py <config.json>")
        return None
    if not argv[1].lower().endswith(".json"):
        print("Error: the configuration file must be a .json file.")
        return None
    return argv[1]


def main(argv: list[str]) -> int:
    """Parse arguments, load the config and launch the game.

    Args:
        argv: The full ``sys.argv`` list.

    Returns:
        A process exit code (0 on success, non-zero on a usage error).
    """
    path = _resolve_config_path(argv)
    if path is None:
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
