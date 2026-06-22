_This project has been created as part of the 42 curriculum by kpanfero


# Fly-In — Drone Routing Simulation

## Description

**Fly-In** is a drone routing simulation system that efficiently navigates a fleet
of drones from a central start hub to a target end zone through a connected
network of zones. The algorithm minimises total simulation turns while
respecting strict zone-capacity, link-capacity, and movement-cost constraints.

The system parses a custom map file format describing the network topology,
schedules drone movements turn-by-turn, and outputs a step-by-step transcript
of all drone movements.

### Key Features

- **Custom map parser** with full validation and clear error messages
- **Multi-path flow scheduler** that distributes drones across diverse routes
- **Capacity-aware scheduling** for both zones (`max_drones`) and links
  (`max_link_capacity`)
- **Restricted-zone transit** support (2-turn moves)
- **Adaptive optimisation** that auto-tunes path count per map
- **Colored terminal visualisation** of the network and drone movements
- **Optional graphical visualisation** via `matplotlib`
- **Validator** that verifies every transcript respects all spec rules

## Instructions

### Installation

The Makefile automatically creates a virtual environment and installs all
dependencies. On macOS / Linux:

```bash
make install
```

This creates a `.venv` directory in the project root by default.

**On the 42 cluster** (where the home directory has a small disk quota), the
Makefile auto-detects `/sgoinfre/<user>/` or `/goinfre/<user>/` and places
the venv there to avoid filling up your home. You can override with:

```bash
make install VENV_DIR=/sgoinfre/$USER/fly_in_venv
```

Then either activate the venv:

```bash
source .venv/bin/activate     # or your custom path
```

or simply use the Makefile targets which always invoke the venv's Python:

```bash
python3 -m main maps/01_the_impossible_dream.txt --visual
make run MAP=maps/01_linear_path.txt ARGS=--visual
```

### Manual installation (without Makefile)

If you prefer to install manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Running

```bash
# Run the simulation (plain output to stdout)
make run MAP=maps/01_linear_path.txt

# With colored terminal visualisation (drone moves + zone state per turn)
make run MAP=maps/03_ultimate_challenge.txt ARGS=--visual

# With static graphical network display (matplotlib window)
make run MAP=maps/01_the_impossible_dream.txt ARGS="--visual --graph"

# Save static graph as PNG file
python3 -m fly_in.main maps/01_the_impossible_dream.txt --save-graph dream.png
open dream.png   # macOS

# ── Animation: see drone movement on the graph! ──────────────────────────

# Live animated window (close window to exit)
python3 -m fly_in.main maps/01_dead_end_trap.txt --animate

# Save one PNG per turn (turn_001.png, turn_002.png, ...)
python3 -m fly_in.main maps/02_circular_loop.txt --save-frames frames/
open frames/turn_001.png   # view individual frames
# Or assemble into a GIF:
#   brew install imagemagick
#   magick -delay 60 -loop 0 frames/turn_*.png simulation.gif

# Customize animation speed (default 800ms per frame)
python3 -m fly_in.main maps/01_the_impossible_dream.txt --animate --frame-interval 300

# Quiet mode: only the per-turn output (spec format)
make run MAP=maps/01_linear_path.txt ARGS=--quiet

# Manual path-count override (for experimentation)
python3 -m fly_in.main maps/01_the_impossible_dream.txt --paths 6
```

### Makefile Targets

| Target                          | Description                                  |
| ------------------------------- | -------------------------------------------- |
| `make help`                     | Show all targets                             |
| `make info`                     | Show detected Python and venv paths          |
| `make install`                  | Create venv + install dev dependencies       |
| `make install VENV_DIR=/path`   | Install with a custom venv location          |
| `make run MAP=path`             | Run a simulation                             |
| `make run MAP=path ARGS=--visual` | Run with colored output                    |
| `make debug MAP=path`           | Run inside `pdb`                             |
| `make lint`                     | `flake8` + `mypy` (mandatory configuration)  |
| `make lint-strict`              | `flake8` + `mypy --strict`                   |
| `make test`                     | `pytest`                                     |
| `make clean`                    | Remove caches                                |
| `make clean-venv`               | Remove the virtualenv                        |
| `make run-easy1` … `run-hard3`  | Convenience targets for each map             |
| `make run-challenger`           | Run the Impossible Dream                     |
| `make run-all`                  | Run every map, show only turn count          |
| `make run-all-verbose`          | Run every map with full per-turn output      |

## Troubleshooting

### `pip: No such file or directory` (macOS)

The Makefile uses `python3 -m pip` internally — it never calls bare `pip`.
If you see this error, you have an outdated Makefile; pull the latest version.

### `OSError: [Errno 28] No space left on device` (42 cluster)

Your home directory quota is full. Solution: place the venv in a directory
without a quota:

```bash
make clean-venv                                          # remove the bad venv
make install VENV_DIR=/sgoinfre/$USER/fly_in_venv        # install elsewhere
```

The Makefile auto-detects `/sgoinfre/` and `/goinfre/` and uses them
automatically when present, so usually `make install` alone suffices on 42.

### `python3: command not found`

The Makefile probes `python3.11`, `python3.10`, `python3`, and `python` in
order. If none is found, install Python 3.10+ first. On 42 you may need:

```bash
which python3.11 python3.10 python3 python
```

and pass the right one explicitly: `make install PYTHON=/usr/bin/python3.10`.

### `ModuleNotFoundError: No module named 'matplotlib'`

`matplotlib` is optional and only needed for `--graph`. The Makefile
silently skips it if installation fails. Without it, `--visual` (terminal
colors) still works.

## Algorithm & Implementation Strategy

### Architecture

The codebase is fully **object-oriented** and split into clear layers:

```
fly_in/
├── models/          # Core domain objects
│   ├── zone.py            (Zone + ZoneType enum)
│   ├── connection.py      (Connection edge)
│   ├── drone.py           (Drone + DroneState enum)
│   └── graph.py           (Graph: zones + adjacency)
├── parser/
│   └── map_parser.py      (MapParser, ParseError)
├── algorithm/
│   ├── pathfinder.py      (Dijkstra + k-best paths)
│   └── scheduler.py       (Multi-drone turn scheduler)
├── simulation/
│   ├── engine.py          (Adaptive run orchestrator)
│   └── validator.py       (Output rule-compliance checker)
├── visualization/
│   ├── terminal.py        (ANSI-colored terminal output)
│   └── graph_view.py      (matplotlib graph rendering)
└── main.py                (CLI entry point)
```

### Pathfinding

A **modified Dijkstra** walks the graph using zone-type-aware costs
(normal=1, restricted=2, priority=0.9 — slightly biased to encourage
priority routes when costs tie).

The `find_k_best_paths` method finds **k diverse paths** by repeatedly
running Dijkstra while applying penalties to zones used in previously
found paths. This gives the scheduler multiple routes to distribute
drones across.

**Complexity**: each Dijkstra run is `O((V + E) · log V)`; finding k
paths costs `O(k · (V + E) · log V)`. For typical maps (≤50 zones)
this is sub-millisecond.

### Scheduling

The scheduler uses a **flow-based assignment**:

1. Compute k diverse paths (k auto-tuned per map).
2. For each drone, pick the path that minimises
   `path_cost + queue_delay`, where
   `queue_delay = (drones_already_assigned / bottleneck_capacity)`.
   This greedily packs paths up to their bottleneck capacity before
   spilling onto longer routes.
3. Each turn:
   - **Phase 1** — drones currently on a link (mid-restricted-transit)
     must complete their move and arrive at their destination zone.
   - **Phase 2** — waiting drones attempt to advance one step along
     their path. Drones farther along their path move first to avoid
     blocking those behind them. Each move respects link and zone
     capacity, accounting for departures freeing space within the same
     turn.
4. The `SimulationEngine` runs the scheduler with several candidate
   path counts (3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20) and picks
   the configuration with the fewest turns. This adaptive search
   handles maps of all sizes.

### Capacity Handling

- **Zone capacity** (`max_drones`): tracked per turn; departures free
  capacity instantly so a swap (drone A out → drone B in) costs only
  1 turn for B.
- **Link capacity** (`max_link_capacity`): a per-turn counter prevents
  more than N drones traversing the same link simultaneously.
- **Restricted-zone reservation**: when a drone enters a 2-turn link
  it reserves a slot at the destination zone so other drones don't
  fill it before arrival, preventing starvation.

### Performance Results

| Map                        | Turns | Target  | Status |
| -------------------------- | ----- | ------- | ------ |
| 01_linear_path             | 4     | ≤6      | ✅     |
| 02_simple_fork             | 5     | ≤6      | ✅     |
| 03_basic_capacity          | 6     | ≤8      | ✅     |
| 01_dead_end_trap           | 8     | ≤15     | ✅     |
| 02_circular_loop           | 16    | ≤20     | ✅     |
| 03_priority_puzzle         | 7     | ≤12     | ✅     |
| 01_maze_nightmare          | 14    | ≤45     | ✅     |
| 02_capacity_hell           | 18    | ≤60     | ✅     |
| 03_ultimate_challenge      | 29    | ≤35     | ✅     |
| **01_the_impossible_dream**| **45**| =45 (REC)| ✅     |

All targets met "perfectly" (Bonus criterion). The Challenger map
matches the reference record of 45 turns.

## Visual Representation

### Terminal Output (`--visual`)

ANSI color codes highlight:

- **Green** — start/end zones, delivered drones
- **Cyan** — drone movements and current positions
- **Yellow** — restricted zones / transit drones
- **Magenta** — priority zones
- **Red** — blocked zones / dead ends
- **Bold** — section headers and summary

Each turn is printed with the turn number, a vertical separator, and
all drone movements color-coded for readability.

### Graphical Output (`--graph`)

When `matplotlib` is installed, a network diagram is rendered showing:

- Zone positions on a 2-D coordinate plane
- Color-coded zones by type
- Connection edges with line width proportional to link capacity
- Capacity numbers overlaid on each zone
- Legend explaining the color scheme

## Resources

### Algorithmic References

- **Dijkstra's algorithm** for shortest paths (CLRS, Chapter 24)
- **Multi-commodity flow** problems (Ahuja, Magnanti & Orlin,
  *Network Flows*) — inspiration for the path-assignment heuristic
- **Lem-in problem** (42 cursus) — similar multi-agent routing
  challenge that informed the scheduler design
- **k-shortest paths** (Yen's algorithm variant) — adapted using
  zone penalties rather than edge removal

### Python Documentation

- `heapq` — priority queue used in Dijkstra
- `dataclasses` and `enum` — modeling
- `typing` — type hints throughout

### How AI Was Used

AI assistance was used for:

- **Boilerplate reduction**: drafting docstrings, type hints, and
  argument-parser scaffolding.
- **Linting fixes**: catching `flake8`/`mypy` issues and suggesting
  type-safe patterns.
- **Edge-case enumeration**: brainstorming corner cases for the
  parser and validator (duplicate connections, missing fields, etc.).
- **Design review**: discussing the trade-offs between BFS, Dijkstra,
  and flow algorithms for this problem.

All algorithm logic, the scheduler turn-by-turn mechanics, the
capacity-handling rules, and the validation logic were designed
and authored manually. AI-generated suggestions were reviewed,
adapted, and tested before inclusion.

## Project Structure

All files are at the root of the repository:

```
.
├── fly_in/                 # Source package
├── maps/                   # Provided test maps
├── tests/                  # pytest test suite
├── Makefile
├── README.md
├── .gitignore
└── requirements.txt
```
