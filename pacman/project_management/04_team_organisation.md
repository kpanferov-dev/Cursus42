# Team organisation

## Members and primary ownership
- **huwang** — config loader, highscore system, level model, UI/HUD, tests.
- **kpanfero** — maze adapter, entities + ghost AI, cheat mode, packaging.

Both members co-owned the game state machine and the documentation.

## How we worked
- One Kanban card per feature, one Git branch per card.
- Every branch merged through a pull request reviewed by the other member.
- A card only reaches *Done* once `make lint` and `make test` pass.

## How decisions were made
- Small technical choices: decided by the module owner.
- Cross-cutting choices (data formats, state machine, packaging target):
  decided together in the weekly checkpoint, recorded in this directory.

## Key decisions recorded
1. **Plain JSON for highscores** over SQLite/pickle: human-readable, no extra
   dependency, matches the config format.
2. **Fat-wall tile grid** derived from the package's edge-wall encoding:
   simplest mapping to classic Pac-Man movement and rendering.
3. **Reachability-limited dot placement**: guarantees every level is clearable
   regardless of what the assigned generator produces.
4. **PyInstaller one-folder + Itch.io/butler** for distribution: free, fast to
   iterate, and re-buildable on demand during the review.

## How issues were handled
Blocking points were raised immediately on the board and, if not resolved in a
short pairing session, escalated to the weekly checkpoint. See
[06_retrospective.md](06_retrospective.md).
