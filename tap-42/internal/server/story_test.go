package server

import (
	"strings"
	"testing"
	"time"
)

// fight attacks until the enemy dies; it fails if the player is knocked out.
func fight(t *testing.T, p *peer, npc string) int {
	t.Helper()
	for turn := 1; turn <= 20; turn++ {
		got := p.check("ATTACK "+npc, "OK {")
		if strings.Contains(got, `"status":"victory"`) {
			return turn
		}
		if strings.Contains(got, `"status":"respawn"`) {
			t.Fatalf("knocked out by %s: %s", npc, got)
		}
	}
	t.Fatalf("%s never died", npc)
	return 0
}

func walk(p *peer, dirs ...string) {
	p.t.Helper()
	for _, d := range dirs {
		p.check("MOVE "+d, "OK room=")
	}
}

// waitFor reads raw lines until one contains want (events are asynchronous).
func waitFor(t *testing.T, p *peer, want string) {
	t.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if strings.Contains(p.next(), want) {
			return
		}
	}
	t.Fatalf("never received %q", want)
}

// TestStorylineCanBeWon plays the whole main story (and one side quest).
func TestStorylineCanBeWon(t *testing.T) {
	srv, addr := launch(t)
	srv.mu.Lock()
	srv.rateLimit = 10000 // the test plays much faster than a human
	srv.mu.Unlock()
	watcher := join(t, addr, "watcher")
	a := join(t, addr, "hero")

	// Chapters are locked until their prerequisites are done; TALK gives hints.
	a.check("QUEST City Guard", "ERR 406 NO_QUEST_AVAILABLE")
	a.check("TALK City Guard", "OK Keep the peace")
	a.check("TALK Master Cartographer", "OK Before we chase")

	// The forge gate needs the Copper Key from the tavern.
	walk(a, "north")
	a.check("MOVE north", "ERR 302 EXIT_LOCKED")
	walk(a, "south", "south")
	a.check("TAKE Copper Key", "OK taken=item.copper_key")
	walk(a, "north")
	a.check("QUEST Master Cartographer", "OK {")
	walk(a, "north", "north")
	a.check("TAKE Iron Shield", "OK taken=item.iron_shield")
	a.check("TALK Ghost Smith", "OK Clang")
	a.check("QUEST Ghost Smith", "ERR 406 NO_QUEST_AVAILABLE")

	// Chapter 1: deliver the compass. The consumed compass returns to the library.
	walk(a, "south", "east")
	a.check("TAKE Silver Compass", "OK taken=item.silver_compass")
	walk(a, "east")
	a.check("TAKE Rusty Sword", "OK taken=item.rusty_sword")
	a.check("QUEST Marsh Ranger", "ERR 406 NO_QUEST_AVAILABLE")
	walk(a, "west", "west", "south")
	a.check("TALK Master Cartographer", "OK Thank you!")
	a.check("TAKE Old Map Fragment", "OK taken=item.map_fragment")
	walk(a, "north", "east")
	if look := a.check("LOOK", "OK {"); !strings.Contains(look, "item.silver_compass") {
		t.Fatalf("compass did not return to the library: %s", look)
	}

	// Side quest: the notes give a permanent +3 attack.
	a.check("QUEST Old Librarian", "OK {")
	a.check("TALK Old Librarian", "OK Thank you!")

	// Chapter 2: the wraith.
	walk(a, "east")
	a.check("QUEST Marsh Ranger", "OK {")
	walk(a, "south", "south")
	fight(t, a, "Marsh Wraith")

	// Chapter 3: the bandit drops the Star Lens.
	walk(a, "north", "north", "west", "west", "south")
	a.check("QUEST City Guard", "OK {")
	walk(a, "north", "east", "east", "north")
	a.check("MOVE north", "ERR 302 EXIT_LOCKED")
	fight(t, a, "Ruin Bandit")
	if look := a.check("LOOK", "OK {"); !strings.Contains(look, "item.star_lens") {
		t.Fatalf("bandit dropped no lens: %s", look)
	}
	a.check("TAKE Star Lens", "OK taken=item.star_lens")
	walk(a, "north") // the lens opens the sanctum
	a.check("ATTACK Eclipse Warden", "ERR 405 NPC_INVULNERABLE")

	// Chapter 4: starsteel (+8 attack). Sword gone, so 14 + 3 (notes) + 8 = 25.
	walk(a, "south", "south", "west", "west", "north")
	a.check("QUEST Ghost Smith", "OK {")
	a.check("TALK Ghost Smith", "OK Thank you!")
	if st := a.check("STATUS", "OK {"); !strings.Contains(st, `"attack":25`) || !strings.Contains(st, `"defense":4`) {
		t.Fatalf("unexpected stats: %s", st)
	}

	// Chapter 5: the Warden drops the Heart of Time.
	walk(a, "south", "east", "east")
	a.check("QUEST Marsh Ranger", "OK {")
	walk(a, "north", "north") // door stays open for this player
	fight(t, a, "Eclipse Warden")
	a.check("TAKE Heart of Time", "OK taken=item.heart_of_time")

	// Chapter 6: bring the Heart back and win.
	walk(a, "south", "south", "west", "west", "south")
	a.check("QUEST Master Cartographer", "OK {")
	a.check("TALK Master Cartographer", "OK Thank you!")
	if st := a.check("STATUS", "OK {"); !strings.Contains(st, `"victory":true`) {
		t.Fatalf("no victory: %s", st)
	}
	if journal := a.check("QUESTS", "OK ["); strings.Count(journal, `"status":"completed"`) != 7 {
		t.Fatalf("journal: %s", journal)
	}
	a.check("QUEST Master Cartographer", "ERR 406 NO_QUEST_AVAILABLE")
	a.check("TALK Master Cartographer", "OK Tick, tock")
	waitFor(t, watcher, "EVT GLOBAL VICTORY hero")
}

func TestUseItemsAndStoryIntro(t *testing.T) {
	_, addr := launch(t)
	conn := join(t, addr, "healer")
	// The intro event follows the CONNECT reply.
	waitFor(t, conn, "EVT STORY INTRO At midnight")
	conn.check("TAKE Old Map Fragment", "OK taken=")
	conn.check("USE Old Map Fragment", "ERR 400 ITEM_NOT_USABLE")
	conn.check("USE Healing Herbs", "ERR 404 ITEM_NOT_IN_INVENTORY")
	walk(conn, "east")
	conn.check("TAKE Healing Herbs", "OK taken=item.herbs")
	walk(conn, "east")
	fight(t, conn, "Shadow Wolf") // 30 HP: 3 hits, 2 counters of 7
	got := conn.check("USE herbs", "OK {")
	if !strings.Contains(got, `"healed":14`) || !strings.Contains(got, `"hp":100`) {
		t.Fatalf("use: %s", got)
	}
	conn.check("INVENTORY", `OK ["item.map_fragment"]`)
	conn.check("ATTACK City Guard", "ERR 404 NPC_NOT_FOUND")
}
