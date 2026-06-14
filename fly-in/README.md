*This project has been created as part of the 42 curriculum by &lt;your_login&gt;.*

# Fly-in

## Description

Fly-in is a drone-routing simulator. Given a network of connected
**zones**, a number of drones all starting in a single **start** zone must
be routed to a single **end** zone in as few simulation turns as possible,
while respecting a set of movement and capacity constraints.

Zones come in four flavours that affect routing:

| Type | Entry cost | Notes |
|------|-----------|-------|
| `normal` | 1 turn | default |
| `priority` | 1 turn | preferred during pathfinding |
| `restricted` | 2 turns | the drone occupies the connection in transit and **must** arrive the next turn |
| `blocked` | — | impassable; never entered |

Each zone may hold at most `max_drones` drones at once (default `1`; the
start and end zones are unlimited), and each connection may be traversed
by at most `max_link_capacity` drones at once (default `1`). The goal is
to minimise the total number of turns.

The project is written in **Python 3.10+**, is fully type-annotated
(passes `mypy --strict`), adheres to **flake8**, is **object-oriented**,
and uses **no graph libraries** — all graph logic is implemented by hand.

## Instructions

No third-party runtime dependencies are required; only the linters used
for development are listed in `requirements.txt`.

```bash
# install the lint/type-check tooling (optional, for development)
make install

# run the simulation on a map (defaults to maps/example.txt)
make run
make run MAP=maps/fork.txt

# run directly, with options
python3 main.py maps/example.txt            # full coloured feedback
python3 main.py maps/example.txt --quiet    # only the canonical move lines
python3 main.py maps/example.txt --no-color # disable ANSI colours

# debugging, linting, and the rule checker
make debug MAP=maps/restricted.txt          # launches pdb
make lint                                    # flake8 + mypy (subject flags)
make lint-strict                             # flake8 + mypy --strict
make test                                    # independent rule validator
make clean                                   # remove caches
```

### Map format

```
nb_drones: 5
start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
connection: hub-roof1
connection: corridorA-tunnelB [max_link_capacity=2]
```

The first line declares the drone count. Each `start_hub`/`end_hub`/`hub`
line declares a zone with integer coordinates and optional `[...]`
metadata (`zone`, `color`, `max_drones`, in any order). Each `connection`
line links two previously-declared zones with an optional
`max_link_capacity`. Lines beginning with `#` are comments. Any
malformed input stops the program with a message naming the line and the
cause.

### Output format

One line per turn lists the moves of that turn, space separated, as
`D<id>-<zone>`, or `D<id>-<from>-<to>` while a drone is in flight toward a
restricted zone. Drones that do not move are omitted; the run ends once
all drones reach the end zone.

## Algorithm choices and implementation strategy

The code separates three concerns into independent, testable objects.

### 1. Model (`models.py`)
`Zone`, `Connection` and `Network` describe the graph. `ZoneType` is an
`Enum` that also owns the routing semantics of each type (entry cost,
traversability, priority). The network keeps an adjacency map and a
connection table keyed by an order-independent pair so that `a-b` and
`b-a` are the same edge.

### 2. Pathfinding (`pathfinding.py`)
Two hand-written algorithms:

* **Dijkstra** (`shortest_path`) over the *entry cost* of each zone, with
  a secondary key that prefers routes through `priority` zones. This
  honours the weighted-zone requirement (restricted = 2, priority
  preferred).
* **Maximum flow** (`find_lanes`) to obtain capacity-respecting routes.
  Because zones — not just edges — have capacities, each zone is
  **split** into an *in* and an *out* node joined by an edge whose
  capacity is the zone's `max_drones` (unlimited for start/end, `0` for
  blocked). Connections become directed arcs in both directions with
  capacity `max_link_capacity`. A textbook **Edmonds–Karp** routine
  computes the maximum flow from the start's *in* node to the end's *out*
  node; the flow is then decomposed into unit-flow **lanes**. By
  construction, the simultaneous use of these lanes never exceeds any
  zone or connection capacity. Lanes are sorted by cost then length.

Complexity: the flow runs in `O(V·E²)` in the worst case (Edmonds–Karp),
which is comfortable for the map sizes in this subject; Dijkstra is
`O(E·log V)`. Paths are computed once and reused — nothing is recomputed
per turn — so memory is `O(V + E + lanes)`.

### 3. Scheduling (`simulation.py`)
The `Simulator` is the **source of truth**: whatever the pathfinder
proposes, the simulator only ever emits legal moves.

* **Distribution.** Drones are spread across lanes with a greedy
  makespan heuristic: each drone joins the lane with the smallest current
  `cost + load`. This is the classic allocation that minimises the finish
  turn when one drone can enter a lane per turn.
* **Turn resolution.** Each turn proceeds in three phases:
  1. *Arrivals* — drones finishing a restricted (2-turn) transit land in
     their destination. A drone that lands this turn has used its action
     and cannot move again.
  2. *Advances* — remaining drones try to step forward along their lane,
     processed **closest-to-goal first** so a leader vacates a zone before
     a follower needs it (pipelining). A move is taken only if the
     destination still has room and the connection still has capacity.
     Entering a restricted zone reserves the destination slot for the
     arrival turn (modelled by occupying it during transit), which
     guarantees the "must arrive next turn" rule can always be honoured.
  3. *Rotation breaking* — if a group of waiting drones forms a cycle
     where each wants the cell another is leaving, they are rotated
     simultaneously (legal because every zone keeps the same occupancy).
* **Safety.** Drones wait rather than make an illegal move, and a turn
  ceiling guards against any unexpected non-progress.

Because the simulator enforces every rule itself, the output is always
valid even on adversarial maps; the pathfinder's job is purely to make it
*fast*.

### Adaptability
Different topologies are handled by the same pipeline: disjoint paths fall
out of the flow as separate lanes, shared zones are governed by their
capacities, weighted/restricted zones are priced into both the flow and
the scheduler, and loops are tolerated by the rotation breaker.

## Visual representation features

Running without `--quiet` produces coloured terminal feedback that makes
the simulation easier to follow and to evaluate:

* a **network overview** — drone/zone/connection counts, the start and
  end, and every zone printed in its own `color` with a glyph for its
  type (`o` normal, `*` priority, `!` restricted, `x` blocked) and its
  capacity;
* the **lanes** the pathfinder selected, with their costs;
* the **per-turn movements**, with each destination painted in its zone's
  colour so a reader can track where drones flow;
* a **summary** of secondary metrics (total turns, drones delivered, total
  moves, average moves per drone) to support peer comparison.

Colours are emitted only when the output is a real terminal and can be
forced off with `--no-color`, so piping `--quiet` output stays clean and
machine-readable.

## Resources

* Maximum-flow background: the Ford–Fulkerson method and the
  Edmonds–Karp BFS refinement (any standard algorithms text, e.g. CLRS,
  *Introduction to Algorithms*, chapter on maximum flow).
* Vertex-capacity handling via **node splitting** (a classic max-flow
  modelling technique).
* Dijkstra's shortest-path algorithm for weighted graphs.
* Python typing and `mypy` documentation; the `flake8` style guide
  (PEP 8) and PEP 257 for docstrings.

### How AI was used

An AI assistant was used as a design and drafting aid: to discuss the
overall architecture (separating model, pathfinding and scheduling), to
sketch the node-split max-flow formulation and the turn-resolution
phases, to draft the module code and docstrings, and to help build test
maps and the independent rule validator. Every algorithmic decision was
reviewed and tested (see `tests/validator.py`, which re-checks each run
against the rules from scratch). Per the subject's AI guidance, the code
here should be read, understood, and — where useful — reworked by the
author before evaluation, since you must be able to explain and defend
every line.
