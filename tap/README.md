*This project has been created as part of the 42 curriculum by huwang, kpanfero.*

# TAP — The Answer Protocol (RFC 42TAP)

## Description

TAP is a multiplayer, in-memory text adventure implemented in **Go**. A line-oriented **TCP server** maintains the shared game world and exposes the protocol described by the accompanying `RFC-42TAP.html`. Players may connect through a fully asynchronous **terminal CLI** or the interactive **browser GUI** (served by a small Go HTTP/SSE-to-TCP bridge). Both clients speak to the same unmodified TAP server; the GUI bridge opens one real TAP TCP session per browser player.

Features: a complete **storyline you can win** (*The Stopped Clock*: 6 chained main quests, 2 side quests, 5 monsters including a final boss); twelve rooms with multiple cycles, optional branches and **locked doors**; ten unique items (keys, weapons, armour, healing items, boss loot) with ID/name lookup; dialogue/quest-giving/enemy NPCs; cooperative chat and groups; an **English activity chat** that narrates every action in both clients; a **live map** showing your position in both clients; an **illustrated scene view** with clickable characters, items and exits plus an **animated combat screen** in the GUI; turn-based combat and respawns; fully concurrent TCP handling; JSON world validation; structured JSON logs; multiplayer integration tests.

## Instructions

Prerequisites: **Go 1.22+**, `make` and a modern browser (for the GUI). No third-party Go modules are necessary. All project code is Go, HTML, CSS or browser-side JavaScript; **Python is not used**.

From the repository root, open separate terminal windows:

```sh
make install
make build
make run-server                      # TCP localhost:4242
make run-client NAME=alice           # first player (CLI)
make run-client NAME=bob             # second player (CLI)
make run-client-gui                  # browser: http://127.0.0.1:8080
```

Use either or both clients; each browser tab connects as its own uniquely named player. The GUI is a **real HTML/JavaScript GUI**, not `curses`. `make run-client-gui` starts a small Go HTTP service that uses server-sent events (SSE) to stream incoming TCP lines; commands are posted through the same gateway. It does not change the TAP TCP wire protocol. To connect the GUI to another team's TAP server, set `SERVER_ADDR=host:port` in the make command or use `go run ./cmd/gui -server host:port`.

Important: the default server binds to `127.0.0.1` for safety. For LAN multiplayer, use `go run ./cmd/server -addr 0.0.0.0:4242 -world world/world.json`. Restrict access with a firewall when exposing the server. The GUI's Go HTTP listener also defaults to loopback. The GUI's local catalog (`-world`) contains display labels for *this project's* items and NPCs; for external servers with a different world the GUI still shows/sends canonical IDs and accepts manual display names.

Useful make targets:

| Target | Action |
| --- | --- |
| `make install` | `go mod download` (no external modules) |
| `make build` | Build all 3 executables into `bin/` |
| `make run-server` | Start the TCP world server |
| `make run-client NAME=alice` | Start the CLI player |
| `make run-client-gui` | Serve the GUI and TCP bridge |
| `make lint` | Run `go vet` and check `gofmt` |
| `make format` | Format Go code (`gofmt`) and the browser files (Prettier, needs Node.js) |
| `make test` | All unit and integration tests |
| `make test-race` | All tests with the Go race detector |
| `make clean` | Delete compiled binaries |

### Terminal commands

The CLI intentionally uses **raw RFC command mode**: enter a TAP command exactly as you wish it to be transmitted. Commands are case-insensitive; arguments like item names may contain spaces. The CLI prints all incoming `OK`, `ERR` and asynchronous `EVT` lines while you type.

```text
LOOK
WHO
MOVE north
MOVE east
TAKE Silver Compass
INVENTORY
DROP item.silver_compass
TALK Old Librarian
CHAT GLOBAL Hello everyone
CHAT ROOM Look here!
GROUP CREATE
GROUP INVITE bob
GROUP JOIN alice
CHAT GROUP Hello team
GROUP LEAVE
QUEST Master Cartographer
QUESTS
ATTACK Marsh Wraith
DEFEND
FLEE
STATUS
QUIT
```

Each raw protocol line is followed by its English description (see **Activity messages** below):

```text
TAKE Copper Key
OK taken=item.copper_key
  » You pick up the Copper Key.
EVT ROOM ITEM TAKE bob item.herbs
  » bob picked up the Healing Herbs.
```

CLI flags: `-narrate=false` shows only raw protocol lines; `-raw=false` shows only the English messages; `-map=auto|top|inline|off` controls the map (see **Live map**); `-world <path>` selects the display-name/map catalog (default `world/world.json`; optional). The local command `MAP` prints the map at any time and is **not** sent to the server.

Connection handshake is automatic in CLI and GUI (`OK hello proto=1` followed by `CONNECT <username>`). For protocol interoperability testing, `nc 127.0.0.1 4242` can be used to send commands manually.

## Architecture

```text
   CLI (Go) ── TCP/UTF-8/LF ─┐
                            │
   Browser GUI              ├── TAP world server (Go)
        │                   │   ├─ command dispatcher (one mutex per world)
        ├─ HTTP POST ───────┤   ├─ rooms and unique item state
        └─ SSE events       │   ├─ players / groups / quests / NPC HP
              Go gateway ── TCP      └─ JSON structured logging
```

The server's networking design uses one reader and one writer goroutine per TCP connection. Every session has a bounded outbound queue (128 messages); only its writer goroutine calls `Write` on the socket, avoiding interleaved replies and events. A shared `sync.Mutex` serializes commands that mutate global state (movement, item ownership, group membership, combat and quest rewards). The reader uses `bufio.Scanner` with an explicit 1024-byte application limit so TCP packet fragmentation and coalescing are handled correctly. Socket write deadlines (5s) ensure a blocked receiver cannot indefinitely stop other players; overflowing the queue closes the slow socket and cleanup follows.

On disconnect, the server removes the player from the global player index and group, drops carried items into their last room, and **then** broadcasts room `LEAVE` and player count updates. A player can never own an item in two places. A disconnecting group leader transfers leadership to the alphabetically first remaining member. The game resets on server restart; no persistence is required.

### Activity messages (English narration)

Every action produces a human-readable English message, in **both** clients:

- **CLI:** printed under each raw line, prefixed with `»`.
- **GUI:** shown as subtitles under the scene picture (the latest messages). The chat panel's Global / Room / Group tabs keep only chat messages, with an unread counter on each tab.

What is narrated:

| Source | Example |
| --- | --- |
| Your successful commands | `You head north and arrive at Moonlight Market.` · `You strike the Marsh Wraith for 14 damage (21 HP left). It hits back for 9 damage; you have 91 HP.` |
| Your errors | `You can't go "up" from here.` · `The City Guard is not hostile; you can't attack them.` |
| Other players (via events) | `bob entered the room.` · `bob picked up the Silver Compass.` · `bob strikes the Marsh Wraith for 14 damage and defeats it!` |
| Chat, groups, quests, respawns | `bob says to everyone: hi` · `alice invited you to their group. Type GROUP JOIN alice to accept.` · `Quest complete: "A True North"! You earned 25 gold and 10 HP.` |

**Design.** Narration is produced **client-side** by one shared Go package, `internal/narrator`, so the CLI and the GUI produce identical messages. The **TAP wire protocol is unchanged**, so the server stays RFC-compatible and the narrator also works against other teams' servers (it falls back to humanized IDs when their world differs from our catalog). Replies are matched to commands in FIFO order: each command gets exactly one `OK`/`ERR`, and `EVT` lines never consume a command. Your own events (e.g. your own `EVT ROOM ITEM TAKE`) are not repeated, because the reply already described them.

In the GUI, the Go bridge runs the narrator for each session and sends messages as a separate SSE event type (`event: narration`) alongside the raw lines. Automatic GUI refreshes (periodic `LOOK`/`WHO`, refreshes after actions) are posted with `"quiet": true`. They still update the panels, but they are not narrated and their replies are hidden from the protocol log, so the scene subtitles only show what actually happened. If a username is rejected at connect time, the bridge also returns an English explanation (`message`).

### Live map (CLI and GUI)

Both clients show a map of the world with **your current position, updated after every move**, flee, respawn or LOOK.

**CLI.** On a real terminal, the map is **pinned to the top of the screen** and redrawn in place whenever you move. Protocol lines and English messages scroll underneath it, using an ANSI scroll region. Your room is marked `@` and highlighted:

```text
You are here: Glass Garden   (exits: north, east, west)
                         [Forgotten Forge     ]                            [Fallen Observatory  ]
                                    |                                                 |
                         [Moonlight Market    ]---[The Silent Library  ]---[East Watchtower     ]
                                    |                        |                        |
[Old Harbor          ]---[Clockwork Square    ]---[@Glass Garden       ]---[Whispering Forest   ]
                       \            |                                                 |
                         [Copper Kettle Tavern]                            [Murkfen Marsh       ]
Long paths (exit to take in brackets):
  Old Harbor (south) <-> Murkfen Marsh (west)
@ = you are here
```

If output is not a terminal, or the terminal is too small, the map is printed after each move instead (`-map=inline`). Room labels shrink to fit the terminal width, the map is redrawn when the window is resized, and the terminal is restored on `QUIT` or Ctrl+C. Use `NO_COLOR=1` to disable highlighting.

**GUI.** A **Map** panel (SVG) highlights your room with a pulsing "YOU ARE HERE" marker. A **📍 location badge** in the sticky header stays visible while you scroll; next to the connection status, a **QUIT** button (shown only while connected) sends `QUIT`. Between the logo and the location badge, the header also shows your live stats (players in the room, players on the server, HP, gold, attack and defense, plus a 🏆 Champion mark after winning) and a **Refresh room** button (`LOOK`). Neighbouring rooms are labelled with their direction (e.g. `NORTH →`); clicking one (or pressing Enter on it) sends `MOVE <direction>`. Visited rooms have a brighter border.

**Design.**

- The map is computed **client-side** by one shared Go package, `internal/worldmap`, and the **TAP protocol is unchanged**.
- Your position comes from standard replies: `OK connected` (start room), `OK room=<id>` (MOVE/FLEE), `LOOK` JSON and the `EVT PLAYER RESPAWN` extension.
- In the GUI, the bridge sends the layout as an `event: map` SSE message whenever it changes.
- **Layout.** Rooms may declare an optional grid position in `world/world.json` (`"map": [x, y]`, with y growing southwards). The world validator rejects malformed or overlapping positions. Rooms without a position are placed automatically: the client walks the exits breadth-first and puts each neighbour in its exit's direction (the nearest free cell if taken).
- **Long paths.** Our world contains the 5-room loop square → garden → forest → marsh → harbor → square. A loop with an odd number of rooms can never be drawn exactly on a square grid, so one passage is shown as a **long path**: a dashed curve in the GUI, listed under the map in the CLI. Diagonal neighbours are joined with `/` or `\`.
- **Other teams' servers.** Without our catalog, the map is **discovered as you play**. Rooms you have seen exits to appear as `?` (not explored). The CLI sends a hidden `LOOK` after entering an unexplored room, and the GUI refreshes with `LOOK` after each action anyway.

GUI fix included with this change: GUI commands are now posted **strictly in order**. Previously, the parallel refresh requests (`LOOK`, `INVENTORY`, `STATUS`, …) could reach the server out of order, so replies were matched to the wrong command (for example, HP showing `?`).

### Scene view and combat screen (GUI)

At the top of the GUI, a **Scene** panel shows an illustration of the room you are in. You can play the whole game from there:

| In the picture | Action (TAP command sent) |
| --- | --- |
| Arrows at the edges (`▲ North · Moonlight Market`) | Your hero walks off-screen and you `MOVE <direction>`. A 🔒 marks a door that needs an item. |
| A character (✦ = quest giver, ⚔ = enemy) | A menu with 💬 Talk (`TALK`, the answer appears as a **speech bubble**), 📜 Quest (`QUEST`) and ⚔ Attack (`ATTACK`) |
| An item on the ground | Picked up with a small animation (`TAKE`) |
| Your hero, or 🎒 Bag | Your inventory with Use (`USE`) and Drop (`DROP`) |
| Another player | Wave (`CHAT ROOM`), Invite (`GROUP INVITE`), Join (`GROUP JOIN`) |
| Bottom bar | Look, Status, Quests, Who, Create/Leave group, and a **raw TAP command** box that sends any command exactly as typed (e.g. `CHAT ROOM hi`, `GROUP INVITE bob`) |

The English activity messages appear as subtitles under the picture.

**Combat screen.** `ATTACK` opens a fight screen inside the scene: you on one side, the monster on the other, each with an HP bar. Every turn is animated: your hero lunges, the monster flashes with a floating damage number, then it strikes back.

- **Attack**, **Defend** (shield glow), **Use item** (green heal number) and **Flee** buttons send the matching commands.
- **Killing the monster:** it dissolves and a **🏆 VICTORY!** message appears with confetti, plus any loot ("The Ruin Bandit dropped the Star Lens!") and completed quests.
- **FLEE:** your hero runs away and the screen closes.
- **Getting knocked out** shows **💀 DEFEATED**.
- **Attacking the Warden without starsteel** shows **🛡 INVULNERABLE** and names the quest you need.
- **Other players** hitting the same monster appear on your screen too. If a teammate lands the final blow, you get a **🏆 TEAM VICTORY!** screen naming who finished it (quest credit goes to the killer); the killer's victory screen thanks the players who helped.

When you win the game, Clockwork Square turns to **dawn** and the clock starts ticking again.

**How it's built.**

- `cmd/gui/scene.js` and `cmd/gui/scene.css` (like `ui.html`, `ui.css` and `ui.js`) are embedded in the GUI binary and served at `/scene.js` and `/scene.css`.
- **All artwork is original inline SVG drawn in code:** 12 animated room illustrations, 10 item icons, and characters: **players and friendly NPCs are cute cats and rabbits** (cats wag their tails). **Player skins are persistent:** your animal, fur, coat and cape are computed only from your username (case-insensitive FNV-1a hash), so every client draws you the same way on every screen, in every room, in the fight screen and in later sessions. The connect form previews your character as you type your name, while the 5 monsters keep their menacing look. There are no image files and nothing is downloaded.
- Rooms of other teams' worlds get a generic landscape and generic sprites.
- The scene only sends ordinary TAP commands and reads ordinary replies and events. Nothing changes on the server or in the protocol.
- Animations are pure CSS and respect the system "reduce motion" setting.

### Directory layout

```text
cmd/server/main.go        TCP server entry point
cmd/client/main.go        CLI entry point
cmd/gui/main.go           HTTP GUI launcher; embeds and serves the browser files below
cmd/gui/ui.html           Page structure of the browser interface
cmd/gui/ui.css            Page layout and theme ("Midnight ball": night-sky glass panels, storybook type)
cmd/gui/ui.js             Connection, command queue, map, quest journal and chat
cmd/gui/scene.js, scene.css  Illustrated scene view + animated combat screen (original SVG art)
cmd/gui/fonts/            IM Fell English + EB Garamond, bundled so the GUI works offline (SIL OFL, see OFL.txt)
internal/server/          Protocol, command router and game engine + tests
internal/bridge/          HTTP/SSE gateway to the TCP server (+ narration SSE events) + tests
internal/narrator/        Shared English narration of TAP replies/events (CLI + GUI) + tests
internal/worldmap/        Shared live map: position tracking, grid layout, ASCII/JSON rendering + tests
cmd/client/term_*.go      Terminal size / resize helpers for the pinned CLI map
internal/world/           JSON schema validation + tests
world/world.json          Rooms, exits, items, NPCs, quests
RFC-42TAP.html            Reference protocol (provided with the subject)
Makefile, go.mod          Build and Go module metadata
```

## Protocol Implementation

The core wire protocol follows the provided **RFC 42TAP** file, including TCP/LF/UTF-8, greeting, CONNECT, the canonical response prefixes, exact documented error codes, and the required event categories. Successful LOOK and INVENTORY return compact JSON after `OK `. IDs remain stable even when display names contain spaces.

**Implemented RFC command set**: `CONNECT`, `LOOK`, `MOVE`, `CHAT GLOBAL|ROOM|GROUP`, `TAKE`, `DROP`, `INVENTORY`, `TALK`, `ATTACK`, `STATUS`, `QUEST`, `QUESTS`, `WHO`, `GROUP CREATE|INVITE|JOIN|LEAVE`, `QUIT`. **Additional local commands**: `DEFEND`, `FLEE`, `USE <item>` (explicitly allowed as design choices in the subject and RFC's implementation notes).

**Standard outbound RFC events**:

```text
EVT ROOM PRESENCE ENTER <username>
EVT ROOM PRESENCE LEAVE <username>
EVT ROOM CHAT <username> <message>
EVT GLOBAL CHAT <username> <message>
EVT GROUP INVITE <leader>
EVT GROUP JOIN <username>
EVT GROUP LEAVE <username>
EVT GROUP CHAT <username> <message>
EVT STATS players=<count>
```

**Documented extensions/deviations** (because the RFC deliberately omits dynamic item and combat notification schemas, several validation errors, and detailed quest/combat mechanics):

| Extension | Purpose |
| --- | --- |
| `EVT ROOM ITEM TAKE <player> <id>` | Prompt clients to refresh a room after item removal |
| `EVT ROOM ITEM DROP <player> <id>` | Prompt clients to refresh room items after drop/disconnect |
| `EVT ROOM NPC RESPAWN <id>` | A defeated NPC respawned |
| `EVT ROOM COMBAT ...` | Announce attack and defensive turns to same-room players |
| `EVT QUEST COMPLETE <quest_id>` | Tell player to refresh journal and status |
| `EVT PLAYER RESPAWN room=<id> hp=35` | Tell player they were returned to the safe start room |
| `EVT STORY INTRO <text>` | Opening of the storyline, sent right after `OK connected` |
| `EVT PLAYER UNLOCK <direction> <item_id>` | The player opened a locked exit with an item |
| `EVT ROOM ITEM LOOT <npc_id> <item_id>` | A defeated enemy dropped an item in the room |
| `EVT ROOM ITEM RESPAWN <item_id>` | A consumed item reappeared at its spawn room |
| `EVT GLOBAL VICTORY <player>` | A player completed the final quest and won the game (sent to everyone) |
| `USE <item>` → `OK {"used","healed","hp","counter_damage"}` | Consume a healing item |
| `ERR 302 EXIT_LOCKED` | The exit needs an item (e.g. a key) |
| `ERR 405 NPC_INVULNERABLE` | The enemy can't be hurt yet (the boss needs the Starsteel quest) |
| `ERR 400 ITEM_NOT_USABLE` | `USE` on an item that has no effect |
| `ERR 400 <reason>` | Unspecified malformed/unsupported request (RFC has no 400 entry) |
| `ERR 403 AUTH_REQUIRED`, `ERR 403 INVITE_REQUIRED` | Authentication and invitation validation |
| `ERR 404 PLAYER_NOT_FOUND`, `ERR 404 GROUP_NOT_FOUND` | Names not listed in RFC's error table |
| `ERR 429 RATE_LIMITED` | Prevent command flooding |

Unknown extensions may be ignored by other teams' clients. Protocol base errors have the exact RFC spellings: `ERR 201 NAME_IN_USE`, `ERR 301 NO_EXIT`, `ERR 401 NOT_IN_GROUP`, `ERR 402 ALREADY_IN_GROUP`, `ERR 404 ITEM_NOT_FOUND`, `ERR 404 ITEM_NOT_IN_INVENTORY`, `ERR 404 NPC_NOT_FOUND`, `ERR 405 NPC_NOT_HOSTILE`, `ERR 406 NO_QUEST_AVAILABLE`. `ERR 900 CONNECTION_FAILED` is returned for rejected/exhausted connections; I/O failures result in logging and/or the CLI/GUI reporting `900`/`901` because delivery is impossible if the underlying socket is broken.

**WHO format conflict in supplied materials**: the PDF example shows `OK {"room":..., "server":5}`, whereas RFC 42TAP §5.2.2 normatively states `OK players=<count>`. This implementation follows the **RFC**. The GUI derives current-room count from the `LOOK.players` array, while `WHO` / `EVT STATS` provide server count. The response to `TALK` is the RFC's plain dialogue text (`OK <dialogue>`), not the optional JSON style illustrated elsewhere. STATUS keeps the RFC fields first (`hp`, `max_hp`, `status`) and adds `gold`, `attack`, `defense` and `victory`; QUEST adds `name`/`reward`, and QUESTS entries add `name`, `description` and `final`. Clients should ignore unknown keys. When an NPC's next quest is still locked by prerequisites, `QUEST` answers the RFC's `ERR 406 NO_QUEST_AVAILABLE` and `TALK` gives a hint.

The protocol document is itself internally inconsistent about `CRLF` in the connection ABNF and `LF` in the general message specification. This implementation transmits `LF`, per the RFC's transport section and the subject's global rules, but also accepts `CRLF` input.

### Interoperability

- A client that implements the documented RFC can connect to this TCP server without the GUI gateway.
- The supplied raw-command CLI can connect to other servers implementing RFC 42TAP.
- The GUI gateway can target a different TCP TAP server using `-server`; it does not require special server endpoints. Its local catalog is advisory only, and users may enter any item/NPC ID or display name.
- The GUI triggers immediate `LOOK` refreshes on this server's extension events, and periodically polls `LOOK`/`WHO` to stay usable with servers that do not send extension events.
- The RFC does not standardize extensions; no claim is made that combat/quest progression is interchangeable between different teams' implementations.

## Storyline: *The Stopped Clock*

> At midnight the Great Clock of Clockwork Square stopped: the Eclipse Warden tore out its Heart of Time and fled to a sealed sanctum above the Fallen Observatory. Until the Heart returns, the night will never end.

The intro arrives as `EVT STORY INTRO` when you connect. **You win** by completing the final quest *Midnight's End*. The server then broadcasts `EVT GLOBAL VICTORY <player>` to everyone, and `STATUS` reports `"victory":true`. Both clients show it: an English message in the CLI, a victory banner in the GUI. You can keep playing afterwards.

### Quests

Main quests unlock in order. Each chapter's giver offers it once the previous chapter is done (`requires` in `world.json`).

| # | Quest | Giver (room) | Goal | Reward |
| --- | --- | --- | --- | --- |
| 1 | A True North | Master Cartographer (Square) | Deliver the **Silver Compass** (Library) | 25 gold, 10 HP |
| 2 | The Marsh Wraith | Marsh Ranger (Watchtower) | Defeat the **Marsh Wraith** (Marsh) | 50 gold, 20 HP |
| 3 | Thief of Stars | City Guard (Square) | Defeat the **Ruin Bandit** (Observatory); he drops the **Star Lens** | 60 gold, 20 HP |
| 4 | Starsteel | Ghost Smith (Forge, *locked*) | Deliver the **Rusty Sword** (Watchtower) | 40 gold, 25 HP, **+8 attack** |
| 5 | The Eclipse Warden | Marsh Ranger (Watchtower) | Open the sealed door with the **Star Lens**, defeat the **Eclipse Warden** (boss); he drops the **Heart of Time** | 100 gold, 30 HP |
| 6 | Midnight's End 🏆 | Master Cartographer (Square) | Deliver the **Heart of Time** | 150 gold, full HP, **VICTORY** |
| side | The Astronomer's Notes | Old Librarian (Library), after 1 | Deliver the **Old Map Fragment** (Square) | 30 gold, **+3 attack** |
| side | Restless Tide | Tavern Keeper (Tavern) | Defeat the **Drowned Sailor** (Harbor) | 40 gold, 25 HP |

**Puzzles and gates.** The forge gate (Market → north) needs the **Copper Key** from the Tavern. The sanctum door (Observatory → north) needs the **Star Lens**. A door, once opened, stays open for that player, so the item can be handed to a teammate. The Warden can't be hurt until you have completed *Starsteel* (`ERR 405 NPC_INVULNERABLE`).

### Walkthrough

`CONNECT` → `TALK Master Cartographer`, then:

1. `QUEST Master Cartographer`. Take the Compass (north, east). Take the Rusty Sword (east). Go back (west, west, south) and `TALK Master Cartographer`.
2. Optional: take the Copper Key in the Tavern (south), then the Iron Shield in the Forge (north, north, north).
3. Optional: take the Old Map Fragment in the Square to the Librarian.
4. `QUEST Marsh Ranger` in the Watchtower, then fight the Wraith (south, south).
5. `QUEST City Guard` in the Square, then fight the Bandit in the Observatory (north of the Watchtower) and `TAKE Star Lens`.
6. In the Forge: `QUEST Ghost Smith`, then `TALK Ghost Smith` with the Rusty Sword.
7. `QUEST Marsh Ranger` again, go north twice into the Eclipse Sanctum, defeat the Warden and `TAKE Heart of Time`. Use `USE Healing Herbs` (Garden) or `USE Loaf of Bread` (Forest) when low.
8. Back in the Square: `QUEST Master Cartographer`, then `TALK Master Cartographer`. **Victory!**

### Quest system design

- Quests are per-player: `not started` → `active` → `completed`. NPCs may offer **several quests in order** (`quests` list); `QUEST <npc>` accepts or reports the NPC's next unfinished quest.
- **Deliver quests** complete on `TALK` while carrying the target item. The item is consumed, then immediately **reappears at its spawn room** (`EVT ROOM ITEM RESPAWN`), so items stay unique and every player can still finish the story.
- **Defeat quests** complete for the player who lands the killing blow.
- **Rewards:** gold, HP (capped at 100), permanent attack bonuses, and victory for the final quest.
- **Dialogue is data-driven** in `world.json`. Each quest has an `offer`, a `reminder` and a `complete` text. NPCs without quests rotate through hint lines (the Merchant tells you where the Copper Key is).
- Progress is validated server-side under the world mutex, logged (`quest_started`, `quest_completed`, `unlock`, `loot`, `victory`), and is **not persisted** across disconnects.

## Combat System

- Each player has **100 HP**. One player command = one turn, and on `ATTACK` the player acts **first**.
- **Player damage** = `14` + best carried weapon (Rusty Sword +4) + permanent quest bonuses (Starsteel +8, Notes +3). It is deterministic, with no randomness.
- **Enemy counterattack** = enemy attack − best carried armour (Iron Shield −4), minimum 1. Civilians refuse combat (`405 NPC_NOT_HOSTILE`).
- **Enemies** (HP / attack): Shadow Wolf 30/7 (Forest), Marsh Wraith 35/9 (Marsh), Drowned Sailor 45/10 (Harbor), Ruin Bandit 55/12 (Observatory, drops Star Lens), **Eclipse Warden 120/16** (Sanctum, boss, needs Starsteel, drops the Heart of Time).
- **Loot:** a defeated enemy drops its loot item in the room, unless that unique item already exists somewhere in the world.
- **`DEFEND`** spends a turn and takes half of the enemy's damage.
- **`USE <item>`** heals: Healing Herbs +35, Loaf of Bread +20. The item is consumed and grows back at its spawn room after 30 s. Used during combat, it costs a turn and the enemy hits back.
- **`FLEE`** ends combat and returns you to the Square. Normal `MOVE` is refused while in combat.
- **Death:** at 0 HP you respawn in the Square with **35 HP**, keeping inventory and quests. A defeated enemy respawns **25 s** later at full HP.
- **Shared fights:** NPC HP is global state, so players can fight the boss together. Only the killing blow completes the quest.
- **Combat results** are JSON (`attacker_hp`, `target_hp`, `damage`, `counter_damage`, `status`), broadcast to the room via `EVT ROOM COMBAT`.

## World Design

Twelve rooms form several circuits, including:

```text
Loop A: loc.square -> loc.garden -> loc.forest -> loc.marsh ->
        loc.harbor -> loc.square
Loop B: loc.square -> loc.market -> loc.library -> loc.garden ->
        loc.square
Branches: loc.market -> loc.forge (locked: Copper Key);
          loc.tower -> loc.ruins -> loc.sanctum (locked: Star Lens)
Other links: loc.library <-> loc.tower <-> loc.forest;
             loc.square <-> loc.tavern <-> loc.harbor
```

The diagram is schematic; **`world/world.json` is authoritative** for connections.

**NPCs:**

- **Quest givers:** Cartographer, Guard, Librarian, Ranger, Innkeeper and Ghost Smith.
- **Dialogue only:** the Merchant.
- **Enemies:** Wolf, Wraith, Drowned Sailor, Bandit and the Warden.

**Items:** every item has a unique world ID. It begins in a specific room, or as an enemy's loot. `TAKE` transfers ownership atomically; `DROP` and unexpected disconnects return ownership to a room. Both `TAKE Silver Compass` and `TAKE item.silver_compass` work; case-insensitive display name matching supports multi-word names.

**World schema (all new fields optional):**

- Items: `heal`, `attack`, `defense`.
- Rooms: `locks` and `map`.
- NPCs: `quests`, `loot` and `requires_quest`. The legacy `quest` field still works.
- Quests: `requires`, `reward_attack`, `offer`, `reminder`, `complete` and `final`.
- A top-level `story` (`title`, `intro`, `victory`).

The loader validates all of it: references to rooms, items, NPCs and quests, door items that can actually be obtained, delivery targets that spawn or drop somewhere, **no cycles in quest prerequisites** (so the story is always finishable), single-line story text, plus the original checks (reachability, unique spawns, minimum counts). Invalid worlds fail at startup.

## Server Logging

The server writes **structured JSON** records via Go's `log/slog` to **stderr**. Each record contains a high-precision RFC3339 timestamp, level (`INFO`, `WARN`, `ERROR`), event category and structured fields such as player, IP, command, args, response, item ID, NPC, room, and outcome.

Events logged include connections (timestamp/IP), disconnects, every inbound command, outbound responses/events (including errors), movement, item take/drop, NPC dialogue, group membership, combat, quest start/completion and NPC respawns. Excessive command bursts trigger `WARN command_flood` (30+ commands/sec), rapid connections from one IP trigger `WARN rapid_connections`, and a slow outbound consumer triggers `WARN slow_client`.

Example monitoring and capture:

```sh
make run-server 2> server.jsonl
# Separate terminal:
tail -f server.jsonl
# With jq installed:
jq 'select(.event=="quest_completed" or .event=="command_flood")' server.jsonl
```

Logging uses synchronous `slog` output to stderr; writes are serialized by Go's logging implementation. For production-scale throughput an asynchronous log sink would be preferable, but the design is appropriate for the assignment's small server and makes failures observable.

## Group Contributions

**Replace these placeholders truthfully before submitting.** The PDF requires a group of 2–3 learners, meaningful contributions from each, and commits by every group member.

| Actual 42 login | Contribution (fill in after implementing/reviewing) |
| --- | --- |
| `<login1>` | Server concurrency, TCP command handling, logging and tests |
| `<login2>` | Browser GUI, Go gateway, world content and quest documentation |
| `<login3>` (optional) | CLI, integration tests, build tooling and reviews |

Suggested Git workflow: `main` with feature branches for `server`, `gui`, and `world-tests`, peer-reviewed pull requests, and purposeful commit messages. Do not claim contributions not actually performed.

## Building and Running

The project uses Go modules and Make as documented under **Instructions**. It requires no platform-specific graphics bindings or C libraries. Run `make lint && make test && make build` before peer evaluation. For the actual evaluation, run server + two clients (one may be GUI) and demonstrate dynamic item transfer, simultaneous chat, group invites, room presence, quest completion, defense, and death/respawn.

## Testing

Automated tests under `internal/world` and `internal/server` use real ephemeral TCP listeners and TCP client sessions:

```sh
make test
make test-race
make lint
```

`internal/server/story_test.go` **plays the whole storyline to victory over TCP**. It checks every gate on the way: locked doors, prerequisites, the invulnerable boss, loot, consumed items returning, `USE`, the global victory event and all 7 quests completed. The tests cover minimum world contents and a cycle, invalid world references and duplicate item spawns; greeting and authentication; Unicode usernames; case-insensitive username collision; wrong commands; room LOOK JSON; movement and invalid exits; item uniqueness and transfer between players; multi-line command handling; group create/invite/join/leave and group chat; successful delivery and combat quests; NPC victory and state; counts after disconnect; status and response shape. `internal/narrator` tests the English messages for replies, errors, events, quiet commands and missing catalogs. `internal/worldmap` tests position tracking (connect, move, respawn, LOOK), the catalog layout and its single long path, 80-column ASCII output, and map discovery on an unknown world. `internal/bridge` runs an end-to-end real TCP server → HTTP bridge → SSE test that checks the narration and map streams. `internal/world` also rejects overlapping map positions.

### Manual multiplayer demo

1. Start `make run-server`, connect `alice` in CLI and `bob` in a browser at `http://127.0.0.1:8080`.
2. Both move `north`, `east` to the Library. `alice` uses `TAKE Silver Compass`; `bob` now sees it disappear and receives `ERR 404 ITEM_NOT_FOUND` if trying to take it. `alice` drops it; `bob` takes it.
3. Use `CHAT ROOM ...` in both clients, then `GROUP CREATE`, `GROUP INVITE bob`, `GROUP JOIN alice` and `CHAT GROUP ...`.
4. As Alice, move to the Square, `QUEST Master Cartographer`, retrieve the compass (Bob must drop it), and `TALK Master Cartographer` to complete it.
5. Move to the Tower, accept `QUEST Marsh Ranger`, move to the Marsh, then attack the Wraith three times (twice with the Rusty Sword); `QUESTS` and `STATUS` show completion and rewards.
6. Attack the stronger Bandit in the Ruins. Use `DEFEND` / `FLEE` and, if desired, take enough attacks to demonstrate respawn at 35 HP.
7. Show a locked door (`MOVE north` from the Market without the Copper Key), then follow the **Walkthrough** to win: every client sees `EVT GLOBAL VICTORY`.
8. Disconnect a player holding an item. The survivor can find that unique item where the disconnected player stood. Check `EVT STATS` and JSON logs for the leave event.

### Security / limitations

Authentication is username uniqueness only (as in the RFC); do not put this server on the public Internet without authentication/rate limiting at the network boundary. Command lines are capped at 1024 bytes, usernames at 32 Unicode code points, active sessions at 128 and inventory slots at 32. Commands are case-insensitive, UTF-8 strings are checked, control characters are rejected, and every client is cleaned up after disconnect. A basic flood threshold and rapid-connect warning are included. No persistent account/quest/item storage is provided, as permitted by the PDF.

## Resources

- `RFC-42TAP.html` — attached TAP transport, commands, response structures, events and errors; primary implementation reference.
- `answer.pdf` (subject supplied separately) — TAP v1.4 minimum features, constraints and evaluation requirements.
- [Go `net` package documentation](https://pkg.go.dev/net) — sockets and TCP listener lifecycle.
- [Go `bufio` package documentation](https://pkg.go.dev/bufio) — complete line framing over fragmented TCP streams.
- [Go `sync` package documentation](https://pkg.go.dev/sync) — shared world state protection.
- [Go `log/slog` package documentation](https://pkg.go.dev/log/slog) — structured server logging.
- [MDN Server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) — browser event delivery.

### Use of AI

Animations