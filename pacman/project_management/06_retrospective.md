# Retrospective — blocking points & conflicts

## Blocking points
1. **Misleading package quick-start.** The A-Maze-ing README showed
   `MazeGenerator(width=.., height=..)`, but the real constructor takes
   `size=(w, h)`. We lost about half a day before reading the wheel's source.
   *Resolution:* trust the source over the docs; the adapter now documents the
   verified signature so the next reader doesn't repeat the mistake.

2. **Window size on large levels.** Big mazes (e.g. 31×31 cells → 63×63 tiles)
   produced very large windows. *Resolution:* the renderer resizes per level;
   we kept the default level list within comfortable sizes and documented the
   `(2w+1)×(2h+1)` expansion in the README.

3. **Ghosts occasionally oscillating in dead-ends.** Early AI reversed
   direction every frame. *Resolution:* forbid reversing unless it is the only
   option, matching classic ghost behaviour.

## Conflicts / disagreements
- **Highscore storage format.** One of us preferred SQLite; the other plain
  JSON. We chose JSON for simplicity and zero dependencies, and noted SQLite
  as a possible future change. Decision made jointly at the weekly checkpoint.

## What went well
- Isolating the maze package behind a single adapter paid off immediately.
- The lint + test gate caught regressions before they reached `main`.

## What we'd do differently
- Write the reachability test earlier — it would have surfaced the
  unclearable-level bug (B1) before manual play did.
