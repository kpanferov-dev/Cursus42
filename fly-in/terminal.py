"""Terminal color visualization for drone simulation.

Provides colored output using ANSI escape codes to display
drone movements and zone states in the terminal.
"""

import sys
from typing import Dict, List
from zone import Zone, ZoneType
from drone import Drone
from graph import Graph


# ANSI color codes
class Colors:
    """ANSI terminal color codes."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    # Foreground
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"


# Rainbow color sequence for 'rainbow' zones
RAINBOW_COLORS = [
    Colors.BRIGHT_RED,
    Colors.BRIGHT_YELLOW,
    Colors.BRIGHT_GREEN,
    Colors.BRIGHT_CYAN,
    Colors.BRIGHT_BLUE,
    Colors.BRIGHT_MAGENTA,
]


def supports_color() -> bool:
    """Check if the terminal supports ANSI color codes.

    Returns:
        True if color output is supported.
    """
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class TerminalVisualizer:
    """Renders colored terminal output for the drone simulation."""

    # Zone type to color mapping
    ZONE_TYPE_COLORS: Dict[str, str] = {
        "normal": Colors.BLUE,
        "restricted": Colors.BRIGHT_YELLOW,
        "priority": Colors.BRIGHT_CYAN,
        "blocked": Colors.RED,
        "start": Colors.BRIGHT_GREEN,
        "end": Colors.BRIGHT_GREEN,
    }

    # Map color names to ANSI codes
    # (excluding "rainbow" which is handled specially)
    COLOR_MAP: Dict[str, str] = {
        "green": Colors.BRIGHT_GREEN,
        "red": Colors.BRIGHT_RED,
        "blue": Colors.BRIGHT_BLUE,
        "yellow": Colors.BRIGHT_YELLOW,
        "orange": Colors.YELLOW,
        "cyan": Colors.BRIGHT_CYAN,
        "purple": Colors.MAGENTA,
        "violet": Colors.MAGENTA,
        "magenta": Colors.BRIGHT_MAGENTA,
        "white": Colors.WHITE,
        "gold": Colors.YELLOW,
        "lime": Colors.BRIGHT_GREEN,
        "brown": Colors.YELLOW,
        "maroon": Colors.RED,
        "crimson": Colors.BRIGHT_RED,
        "pink": Colors.BRIGHT_MAGENTA,
        "gray": Colors.DIM,
        "grey": Colors.DIM,
        "black": Colors.DIM,
        "darkred": Colors.RED,
    }

    def __init__(self, graph: Graph, use_color: bool = True) -> None:
        """Initialize the terminal visualizer.

        Args:
            graph: The drone network graph.
            use_color: Whether to use ANSI color codes. When True,
                colors are emitted unconditionally — useful when the user
                explicitly opts in via --visual. When False, colors are
                disabled.
        """
        self.graph: Graph = graph
        self.use_color: bool = use_color

    def colorize(self, text: str, color: str) -> str:
        """Apply ANSI color to text if color is enabled.

        Args:
            text: Text to colorize.
            color: ANSI color code string.

        Returns:
            Colorized string or plain text if color is disabled.
        """
        if not self.use_color:
            return text
        return f"{color}{text}{Colors.RESET}"

    def _rainbow_text(self, text: str) -> str:
        """Return text with each character colored
            sequentially in rainbow hues.

        Args:
            text: The string to rainbow‑color.

        Returns:
            ANSI‑colored string.
        """
        if not self.use_color or not text:
            return text
        result = []
        for i, ch in enumerate(text):
            color = RAINBOW_COLORS[i % len(RAINBOW_COLORS)]
            result.append(f"{color}{ch}")
        result.append(Colors.RESET)
        return "".join(result)

    def zone_color(self, zone: Zone) -> str:
        """Determine the display color for a zone.

        For 'rainbow' zones, this returns a special marker; actual coloring
        is handled in format_zone.

        Args:
            zone: Zone to get color for.

        Returns:
            ANSI color code string, or a placeholder for rainbow.
        """

        if zone.color:
            lower = zone.color.lower()
            if lower == "rainbow":
                # Return a sentinel; handled in format_zone
                return "RAINBOW"
            if lower in self.COLOR_MAP:
                return self.COLOR_MAP[lower]

        return self.ZONE_TYPE_COLORS.get(zone.zone_type.value, Colors.WHITE)

    def format_zone(self, zone: Zone, drone_count: int = 0) -> str:
        """Format a zone for display.

        Args:
            zone: Zone to format.
            drone_count: Current number of drones in zone.

        Returns:
            Formatted string representation.
        """
        color = self.zone_color(zone)
        tag = ""
        if zone.is_start:
            tag = "[START]"
        elif zone.is_end:
            tag = "[END]"
        elif zone.zone_type == ZoneType.RESTRICTED:
            tag = "[R]"
        elif zone.zone_type == ZoneType.PRIORITY:
            tag = "[P]"
        elif zone.zone_type == ZoneType.BLOCKED:
            tag = "[X]"

        name_str = zone.name
        # Handle rainbow zone names
        if color == "RAINBOW":
            name_colored = self._rainbow_text(name_str)
        else:
            name_colored = self.colorize(name_str, color)

        # Tag and count are always white (or dim)
        tag_colored = self.colorize(tag, Colors.WHITE)
        count_str = f"({drone_count}/{zone.max_drones})"
        count_colored = self.colorize(count_str, Colors.WHITE)

        return f"{name_colored}{tag_colored} {count_colored}"

    def format_drone(self, drone: Drone) -> str:
        """Format a drone for display.

        Args:
            drone: Drone to format.

        Returns:
            Colored drone identifier string.
        """
        if drone.is_delivered:
            return self.colorize(drone.name, Colors.GREEN)
        if drone.is_in_transit:
            return self.colorize(drone.name, Colors.YELLOW)
        return self.colorize(drone.name, Colors.BRIGHT_BLUE)

    def print_header(self, filepath: str) -> None:
        """Print simulation header with map info.

        Args:
            filepath: Path to the map being simulated.
        """
        print(self.colorize("=" * 60, Colors.BOLD))
        print(
            self.colorize(
                "  FLY-IN DRONE SIMULATION",
                Colors.BOLD + Colors.BRIGHT_CYAN))
        print(self.colorize("=" * 60, Colors.BOLD))
        print(f"  Map     : {self.colorize(filepath, Colors.BRIGHT_WHITE)}")
        print(
            f"  Drones  : "
            f"{self.colorize(str(self.graph.nb_drones), Colors.BRIGHT_YELLOW)}"
        )
        print(
            f"  Zones   : "
            f"{self.colorize(str(len(self.graph.zones)), Colors.BRIGHT_WHITE)}"
        )
        links_count = str(len(self.graph.connections))
        links_colored = self.colorize(links_count, Colors.BRIGHT_WHITE)
        print(f"  Links   : {links_colored}")
        assert self.graph.start_zone is not None
        assert self.graph.end_zone is not None
        start_color = self.zone_color(self.graph.start_zone)
        end_color = self.zone_color(self.graph.end_zone)

        start_name = self.graph.start_zone.name
        end_name = self.graph.end_zone.name

        if start_color == "RAINBOW":
            start_formatted = self._rainbow_text(start_name)
        else:
            start_formatted = self.colorize(start_name, start_color)

        if end_color == "RAINBOW":
            end_formatted = self._rainbow_text(end_name)
        else:
            end_formatted = self.colorize(end_name, end_color)
        print(
            f"  Route   : "
            f"{start_formatted}"
            f" → "
            f"{end_formatted}"
        )
        print(self.colorize("=" * 60, Colors.BOLD))
        print()

    def print_turn(self, turn_num: int, tokens: List[str]) -> None:
        """Print a single simulation turn with colored drone tokens.

        Args:
            turn_num: Turn number (1-indexed).
            tokens: List of output tokens for this turn.
        """
        turn_label = self.colorize(f"Turn {turn_num:3d}", Colors.BRIGHT_WHITE)
        formatted_tokens = []
        for token in sorted(tokens):
            parts = token.split("-", 1)
            drone_name = parts[0]
            dest = parts[1] if len(parts) > 1 else ""
            colored = (
                self.colorize(drone_name, Colors.BRIGHT_BLUE)
                + "-"
                + self.colorize(dest, Colors.BRIGHT_WHITE)
            )
            formatted_tokens.append(colored)

        line = "  ".join(formatted_tokens)
        print(f"  {turn_label}  │  {line}")

    def print_turn_with_zones(
        self,
        turn_num: int,
        tokens: List[str],
        zone_occupancy: Dict[str, int],
    ) -> None:
        """Print a turn followed by current zone occupancy state.

        Shows each zone with its name, type, and current/max drone count.
        Zones with drones are highlighted; empty zones are dimmed.

        Args:
            turn_num: Turn number (1-indexed).
            tokens: Output tokens for this turn.
            zone_occupancy: Map of zone_name -> current drone count.
        """
        self.print_turn(turn_num, tokens)
        # Compact zone-state line
        state_parts: List[str] = []
        for zone in self.graph.zones.values():
            count = zone_occupancy.get(zone.name, 0)
            if count == 0:
                continue  # only show zones that have drones
            # Use format_zone which handles rainbow
            formatted = self.format_zone(zone, count)
            # Remove the color from the count
            #  part if we want just a short version?
            # We'll keep full format.
            # For brevity, we can shorten the zone
            #  name if too long, but format_zone does that already.
            state_parts.append(formatted)
        if state_parts:
            indent = " " * 14
            print(f"{indent}└─ {'  '.join(state_parts)}")

    def print_turn_raw(self, turn_num: int, tokens: List[str]) -> None:
        """Print a single turn in required output format (no color).

        Args:
            turn_num: Turn number (1-indexed).
            tokens: List of output tokens.
        """
        print(" ".join(sorted(tokens)))

    def print_graph_state(self, drones: List[Drone]) -> None:
        """Print current state of all zones and drones.

        Args:
            drones: Current list of all drones.
        """
        print(self.colorize("\n  Network State:", Colors.BOLD))
        zone_counts: Dict[str, int] = {}
        for d in drones:
            if not d.is_delivered and not d.is_in_transit:
                z = d.current_zone.name
                zone_counts[z] = zone_counts.get(z, 0) + 1

        for zone in self.graph.zones.values():
            count = zone_counts.get(zone.name, 0)
            if count > 0 or zone.is_start or zone.is_end:
                print(f"    {self.format_zone(zone, count)}")

    def print_summary(
        self,
        total_turns: int,
        nb_drones: int,
        total_moves: int,
    ) -> None:
        """Print final simulation summary.

        Args:
            total_turns: Number of turns taken.
            nb_drones: Number of drones simulated.
            total_moves: Total number of drone movements.
        """
        print()
        print(self.colorize("=" * 60, Colors.BOLD))
        print(
            self.colorize(
                "  SIMULATION COMPLETE",
                Colors.BOLD + Colors.BRIGHT_GREEN))
        print(self.colorize("=" * 60, Colors.BOLD))
        print(
            f"  {self.colorize('Total turns :', Colors.BRIGHT_WHITE)} "
            f"{self.colorize(str(total_turns), Colors.BRIGHT_YELLOW)}"
        )
        print(
            f"  {self.colorize('Drones      :', Colors.BRIGHT_WHITE)} "
            f"{self.colorize(str(nb_drones), Colors.BRIGHT_YELLOW)}"
        )
        print(
            f"  {self.colorize('Total moves :', Colors.BRIGHT_WHITE)} "
            f"{self.colorize(str(total_moves), Colors.BRIGHT_YELLOW)}"
        )
        if total_turns > 0:
            avg = total_moves / total_turns
            print(
                f"  {self.colorize('Moves/turn  :', Colors.BRIGHT_WHITE)} "
                f"{self.colorize(f'{avg:.2f}', Colors.BRIGHT_CYAN)}"
            )
        print(self.colorize("=" * 60, Colors.BOLD))
