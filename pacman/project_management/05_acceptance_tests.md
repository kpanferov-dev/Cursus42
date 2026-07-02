# Acceptance test plan

Legend: ✅ pass · 🐛 bug found (and fixed)

## Configuration & startup
| Scenario | Expected | Result |
|----------|----------|--------|
| No argument (script mode) | Clear usage message, exit 1, no traceback | ✅ |
| Non-`.json` argument | Clear error message, exit 1 | ✅ |
| Missing config file | Defaults used, game runs | ✅ |
| Broken JSON | Defaults used, clear log, no traceback | ✅ |
| Out-of-range values | Clamped to safe range, logged | ✅ |
| Unknown keys | Ignored silently | ✅ |
| Comments (`#`, `//`, `/* */`) | Stripped before parsing | ✅ |

## Maze / level
| Scenario | Expected | Result |
|----------|----------|--------|
| First level seed = 42 | Reproducible maze | ✅ |
| Later levels | Randomised mazes | ✅ |
| Generator missing | `MazeError` handled, menu message | ✅ |
| All dots reachable | Level always clearable | 🐛→✅ (added reachability filter) |
| Super-pacgums in 4 corners | Present and edible | ✅ |
| 4 ghosts, one per corner | Present | ✅ |
| Player starts centre | Yes | ✅ |

## Gameplay
| Scenario | Expected | Result |
|----------|----------|--------|
| Move with arrows / WASD | Player moves through corridors only | ✅ |
| Eat pacgum / super-pacgum | Score increases; ghosts turn edible | ✅ |
| Eat edible ghost | Score +Z; ghost returns home, respawns ~5s | ✅ |
| Ghost touches player | Lose a life; respawn at centre | ✅ |
| Lose all lives | Game-over screen | ✅ |
| Clear all dots | Advance level; keep score + lives | ✅ |
| Clear all levels | Victory screen | ✅ |
| Time runs out | Lose a life (chosen behaviour) | ✅ |
| Pause / resume (P) | Game freezes / resumes | ✅ |
| Highscore qualifies | Name entry (≤10 chars), saved, shown on menu | ✅ |

## Cheats (peer-review aids)
| Key | Expected | Result |
|-----|----------|--------|
| F1 invincibility | No life lost on ghost contact | ✅ |
| F2 skip level | Instantly clears the level | ✅ |
| F3 freeze ghosts | Ghosts stop moving | ✅ |
| F4 extra life | +1 life | ✅ |
| F5 speed boost | Player moves faster | ✅ |
| F6 refill timer | Timer reset | ✅ |

## Packaging
| Scenario | Expected | Result |
|----------|----------|--------|
| `./build.sh` | Produces `dist/pac-man/` + zip | ✅ |
| Launch frozen build, no args | Loads bundled config, plays | ✅ |
| Bundled instructions present | `INSTRUCTIONS.txt` shipped | ✅ |

## Bug log
- **B1 — unreachable dots could make a level unclearable.** Some generated
  layouts left isolated corridor pockets. *Fix:* place dots only on the
  connected component reachable from the player spawn.
- **B2 — packaged build showed the usage error on double-click.** *Fix:*
  detect frozen mode and fall back to the bundled `config.json`.
