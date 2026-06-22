"""Simulation engine for the fly_in drone routing system.

Orchestrates the full pipeline:
1. Parse the map file.
2. Run the scheduling algorithm.
3. Validate the output.
4. Report results.
"""

from typing import Dict, List, Optional
from graph import Graph
from map_parser import MapParser
from scheduler import Scheduler


class SimulationError(Exception):
    """Raised when a simulation rule is violated."""

    pass


class SimulationEngine:
    """Orchestrates the drone routing simulation."""

    def __init__(self, verbose: bool = True, visual: bool = True) -> None:
        """Initialize the simulation engine.

        Args:
            verbose: Whether to print per-turn output to stdout.
            visual: Whether to enable colored visual output.
        """
        self.verbose: bool = verbose
        self.visual: bool = visual
        self.graph: Optional[Graph] = None
        self.turn_log: List[List[str]] = []
        self.stats: Dict[str, float] = {}

    def run_from_file(self, filepath: str) -> List[List[str]]:
        """Parse a map file and run the full simulation.

        Args:
            filepath: Path to the map file.

        Returns:
            Turn log from the simulation.

        Raises:
            ParseError: On map file syntax errors.
            SimulationError: On constraint violations.
            FileNotFoundError: If file not found.
        """
        parser = MapParser()
        self.graph = parser.parse_file(filepath)
        return self._run_simulation()

    def run_from_string(self, content: str) -> List[List[str]]:
        """Parse map content from string and run simulation.

        Args:
            content: Raw map file content.

        Returns:
            Turn log from the simulation.
        """
        parser = MapParser()
        self.graph = parser.parse_string(content)
        return self._run_simulation()

    def _run_simulation(self) -> List[List[str]]:
        """Execute the simulation on the parsed graph.

        Tries multiple path counts and selects the best result.

        Returns:
            Turn log from the best scheduler run.
        """
        assert self.graph is not None
        assert self.graph.start_zone is not None
        assert self.graph.end_zone is not None

        # Try a range of path counts and keep the best
        best_log: List[List[str]] = []
        best_stats: Dict[str, float] = {}
        best_turns = 10**9

        candidate_counts = [3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20]
        strategies = ["farthest", "nearest"]

        for strategy in strategies:
            for n in candidate_counts:
                scheduler = Scheduler(
                    self.graph, num_paths=n, order_strategy=strategy
                )
                try:
                    log = scheduler.run()
                except RuntimeError:
                    continue
                if log and len(log) < best_turns:
                    best_turns = len(log)
                    best_log = log
                    best_stats = scheduler.get_stats()

        self.turn_log = best_log
        self.stats = best_stats
        return self.turn_log

    def get_formatted_output(self) -> str:
        """Return the simulation output in required format.

        Returns:
            Multi-line string, one turn per line.
        """
        lines = []
        for turn_tokens in self.turn_log:
            lines.append(" ".join(sorted(turn_tokens)))
        return "\n".join(lines)

    def print_stats(self) -> None:
        """Print simulation statistics."""
        total_turns = int(self.stats.get("total_turns", 0.0))
        total_moves = int(self.stats.get("total_moves", 0.0))
        avg = self.stats.get("avg_moves_per_turn", 0.0)
        print(f"\n{'='*50}")
        print("  Simulation Complete")
        print(f"{'='*50}")
        print(f"  Total turns    : {total_turns}")
        print(f"  Total moves    : {total_moves}")
        print(f"  Moves per turn : {avg:.2f}")
        if self.graph:
            print(f"  Drones         : {self.graph.nb_drones}")
        print(f"{'='*50}\n")