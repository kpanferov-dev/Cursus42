"""Coloured terminal rendering for the Fly-in simulation.

The :class:`TerminalRenderer` turns a :class:`~simulation.SimulationResult`
into human-friendly, optionally coloured output. Colours come from each
zone's ``color`` metadata; when the destination stream is not a terminal
(or ``--no-color`` is requested) the renderer degrades to plain text.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, TextIO

from models import Network, ZoneType
from pathfinding import Lane
from simulation import SimulationResult

_ANSI: Dict[str, str] = {
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "purple": "35",
    "cyan": "36",
    "white": "37",
    "gray": "90",
    "grey": "90",
    "orange": "33",
}

_TYPE_SYMBOL: Dict[ZoneType, str] = {
    ZoneType.NORMAL: "o",
    ZoneType.PRIORITY: "*",
    ZoneType.RESTRICTED: "!",
    ZoneType.BLOCKED: "x",
}


class TerminalRenderer:
    """Render simulation output with optional ANSI colouring."""

    def __init__(
        self,
        network: Network,
        use_color: bool = True,
        stream: Optional[TextIO] = None,
    ) -> None:
        """Initialise the renderer.

        Args:
            network: The network being displayed.
            use_color: Whether ANSI colour codes may be emitted.
            stream: Destination stream (defaults to standard output).
        """
        self._network = network
        self._stream = stream if stream is not None else sys.stdout
        self._use_color = use_color and self._stream.isatty()

    def _paint(self, text: str, color: Optional[str]) -> str:
        """Wrap ``text`` in an ANSI colour if colouring is enabled."""
        if not self._use_color or color is None:
            return text
        code = _ANSI.get(color.lower())
        if code is None:
            return text
        return f"\033[{code}m{text}\033[0m"

    def render_overview(self, lanes: List[Lane]) -> None:
        """Print a summary of the network and the chosen lanes."""
        self._line("=== Fly-in network ===")
        self._line(f"drones      : {self._network.nb_drones}")
        self._line(f"zones       : {len(self._network.zones)}")
        self._line(f"connections : {len(self._network.connections)}")
        self._line(f"start       : {self._network.start.name}")
        self._line(f"end         : {self._network.end.name}")
        self._line("zones:")
        for zone in self._network:
            symbol = _TYPE_SYMBOL[zone.zone_type]
            capacity = "inf" if zone.is_unlimited else str(zone.capacity)
            label = (f"  [{symbol}] {zone.name} "
                     f"({zone.zone_type.value}, cap={capacity})")
            self._line(self._paint(label, zone.color))
        self._line(f"lanes found : {len(lanes)}")
        for index, lane in enumerate(lanes, start=1):
            arrow = " -> ".join(lane.zones)
            self._line(f"  lane {index} (cost {lane.cost}): {arrow}")
        self._line("")

    def render_turns(self, result: SimulationResult) -> None:
        """Print the per-turn drone movements (the official format)."""
        for number, moves in enumerate(result.moves_per_turn, start=1):
            tokens: List[str] = []
            for drone_id, token in moves:
                zone = self._network.zones.get(token)
                color = zone.color if zone is not None else None
                tokens.append(self._paint(f"D{drone_id}-{token}", color))
            prefix = self._paint(f"turn {number:>3}:", None)
            self._line(f"{prefix} {' '.join(tokens)}")

    def render_plain(self, result: SimulationResult) -> None:
        """Print only the canonical, uncoloured move lines."""
        for line in result.lines:
            self._line(line)

    def render_summary(self, result: SimulationResult) -> None:
        """Print closing performance metrics for the run."""
        drones = self._network.nb_drones
        turns = result.turns
        moved = sum(len(moves) for moves in result.moves_per_turn)
        average = moved / drones if drones else 0.0
        self._line("")
        self._line("=== summary ===")
        self._line(f"total turns         : {turns}")
        self._line(f"drones delivered    : {drones}")
        self._line(f"total drone moves   : {moved}")
        self._line(f"avg moves per drone : {average:.2f}")

    def _line(self, text: str) -> None:
        """Write a single line to the configured stream."""
        self._stream.write(text + "\n")
