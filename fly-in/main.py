"""Command-line entry point for the Fly-in drone router.

Usage::

    python main.py <map_file> [options]

The program parses a map, computes capacity-respecting lanes, simulates
the routing of every drone to the end zone and prints the result. The
canonical per-turn move lines are always produced; richer coloured
feedback is shown unless ``--quiet`` is given.
"""

from __future__ import annotations

import argparse
import sys

from parser import MapParser, ParseError
from pathfinding import NoRouteError, PathFinder
from simulation import Simulator
from visual import TerminalRenderer


class Application:
    """Coordinate parsing, pathfinding, simulation and rendering."""

    def __init__(self, arguments: argparse.Namespace) -> None:
        """Store parsed command-line arguments.

        Args:
            arguments: The namespace returned by :func:`build_parser`.
        """
        self._args = arguments

    def run(self) -> int:
        """Execute the full pipeline.

        Returns:
            A process exit code: ``0`` on success, ``1`` on any handled
            error.
        """
        try:
            network = MapParser().parse_file(self._args.map_file)
            finder = PathFinder(network)
            lanes = finder.find_lanes()
            simulator = Simulator(network, lanes)
            result = simulator.run()
        except ParseError as error:
            return self._fail(f"parse error: {error}")
        except NoRouteError as error:
            return self._fail(f"routing error: {error}")
        except OSError as error:
            return self._fail(f"cannot read map: {error}")
        renderer = TerminalRenderer(
            network, use_color=not self._args.no_color)
        if self._args.quiet:
            renderer.render_plain(result)
            return 0
        renderer.render_overview(lanes)
        renderer.render_turns(result)
        renderer.render_summary(result)
        return 0

    @staticmethod
    def _fail(message: str) -> int:
        """Print an error to standard error and return the failure code."""
        sys.stderr.write(message + "\n")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Route a fleet of drones across a network of zones.")
    parser.add_argument("map_file", help="path to the map description file")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the canonical move lines")
    parser.add_argument("--no-color", action="store_true",
                        help="disable ANSI colour output")
    return parser


def main() -> int:
    """Parse arguments and run the application."""
    arguments = build_parser().parse_args()
    return Application(arguments).run()


if __name__ == "__main__":
    sys.exit(main())
