"""Main entry point for the fly_in drone simulation.

Usage:
    python main.py <map_file> [--visual] [--graph] [--quiet]
"""

import sys
import argparse
from typing import Dict, List, Optional

from map_parser import MapParser, ParseError
from scheduler import Scheduler
from terminal import TerminalVisualizer
from graph_view import GraphVisualizer


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace.
    """
    parser = argparse.ArgumentParser(
        description="fly_in — Drone routing simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py maps/01_linear_path.txt
  python main.py maps/03_ultimate_challenge.txt --visual
  python main.py maps/01_the_impossible_dream.txt --visual --graph
        """,
    )
    parser.add_argument(
        "map_file",
        help="Path to the drone network map file",
    )
    parser.add_argument(
        "--visual",
        action="store_true",
        help="Enable colored terminal output",
    )
    parser.add_argument(
        "--graph",
        action="store_true",
        help="Show static graphical network visualization (matplotlib)",
    )
    parser.add_argument(
        "--save-graph",
        type=str,
        metavar="PATH",
        default=None,
        help="Save the static network graph to a PNG file",
    )
    parser.add_argument(
        "--animate",
        action="store_true",
        help="Show animated drone movement window (matplotlib)",
    )
    parser.add_argument(
        "--save-frames",
        type=str,
        metavar="DIR",
        default=None,
        help="Save one PNG per turn to DIR (turn_001.png, turn_002.png, ...)",
    )
    parser.add_argument(
        "--frame-interval",
        type=int,
        default=800,
        help="Animation frame interval in ms (default: 800)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-turn output; print only final result",
    )
    parser.add_argument(
        "--paths",
        type=int,
        default=0,
        help="Number of candidate paths (0=auto-tune, default: 0)",
    )
    return parser.parse_args(argv)


def run(argv: Optional[List[str]] = None) -> int:
    """Execute the simulation.

    Args:
        argv: Command-line arguments.

    Returns:
        Exit code (0 = success, 1 = error).
    """
    args = parse_args(argv)

    # ── Parse map ──────────────────────────────────────────────────────────
    try:
        parser = MapParser()
        graph = parser.parse_file(args.map_file)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ParseError as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return 1

    # ── Terminal visualizer setup ──────────────────────────────────────────
    vis = TerminalVisualizer(graph, use_color=args.visual)

    if not args.quiet:
        vis.print_header(args.map_file)

    # ── Graphical visualization (static map) ──────────────────────────────
    if args.graph or args.save_graph:
        gv = GraphVisualizer(graph)
        if gv.available:
            if args.save_graph:
                gv.render_static(output_path=args.save_graph)
                print(f"[Info] Network graph saved to: {args.save_graph}")
            else:
                print("[Info] Opening graph window — close it to continue...")
                gv.render_static()
        else:
            print(
                "[Warning] matplotlib not installed. "
                "Run: pip install matplotlib",
                file=sys.stderr,
            )

    # ── Run simulation ─────────────────────────────────────────────────────
    occupancy_log: List[Dict[str, int]] = []
    try:
        if args.paths > 0:
            # Manual path count
            scheduler = Scheduler(graph, num_paths=args.paths)
            turn_log = scheduler.run()
            stats = scheduler.get_stats()
            occupancy_log = scheduler.occupancy_log
        else:
            # Adaptive: try multiple path counts, keep the best result.
            best_scheduler: Optional[Scheduler] = None
            best_turns = 10 ** 9
            for strategy in ("farthest", "nearest"):
                for n in (3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20):
                    sc = Scheduler(
                        graph, num_paths=n, order_strategy=strategy
                    )
                    try:
                        log = sc.run()
                    except RuntimeError:
                        continue
                    if log and len(log) < best_turns:
                        best_turns = len(log)
                        best_scheduler = sc
            if best_scheduler is None:
                print(
                    "Simulation error: no valid schedule found.",
                    file=sys.stderr,
                )
                return 1
            scheduler = best_scheduler
            turn_log = scheduler.turn_log
            stats = scheduler.get_stats()
            occupancy_log = scheduler.occupancy_log
    except RuntimeError as e:
        print(f"Simulation error: {e}", file=sys.stderr)
        return 1

    # ── Output ─────────────────────────────────────────────────────────────
    for turn_num, tokens in enumerate(turn_log, start=1):
        if args.quiet:
            print(" ".join(sorted(tokens)))
        elif args.visual:
            # Show zone state alongside drone moves
            occ = (
                occupancy_log[turn_num - 1]
                if turn_num - 1 < len(occupancy_log)
                else {}
            )
            vis.print_turn_with_zones(turn_num, tokens, occ)
        else:
            # Required output format: plain
            print(" ".join(sorted(tokens)))

    # ── Stats ──────────────────────────────────────────────────────────────
    if not args.quiet:
        vis.print_summary(
            total_turns=int(stats["total_turns"]),
            nb_drones=graph.nb_drones,
            total_moves=int(stats["total_moves"]),
        )

    # ── Animation / per-turn frames ────────────────────────────────────────
    if args.save_frames:
        import os
        gv = GraphVisualizer(graph)
        if not gv.available:
            print(
                "[Warning] matplotlib not installed; cannot save frames.",
                file=sys.stderr,
            )
        else:
            os.makedirs(args.save_frames, exist_ok=True)
            n_digits = max(3, len(str(len(occupancy_log))))
            for i, occ in enumerate(occupancy_log, start=1):
                fname = os.path.join(
                    args.save_frames,
                    f"turn_{i:0{n_digits}d}.png",
                )
                gv.render_with_drones(
                    occ, turn=i, output_path=fname,
                    total_turns=len(occupancy_log),
                )
            print(
                f"[Info] Saved {len(occupancy_log)} frames to "
                f"{args.save_frames}/"
            )

    if args.animate:
        gv = GraphVisualizer(graph)
        if not gv.available:
            print(
                "[Warning] matplotlib not installed; cannot animate.",
                file=sys.stderr,
            )
        else:
            print(
                "[Info] Opening animation window "
                f"({len(occupancy_log)} turns @ {args.frame_interval}ms)"
                " — close window to exit."
            )
            gv.animate(occupancy_log, interval_ms=args.frame_interval)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except BrokenPipeError:
        # Output was piped to a command that closed early (e.g. head, less)
        sys.exit(0)
    except KeyboardInterrupt:
        sys.exit(130)