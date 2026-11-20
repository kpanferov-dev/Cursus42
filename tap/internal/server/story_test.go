package server

import (
	"strings"
	"testing"
	"time"
)

// fight attacks until the enemy dies; it fails if the player is knocked out.
func fight(test *testing.T, client *peer, npc string) int {
	test.Helper()
	for turn := 1; turn <= 20; turn++ {
		got := client.check("ATTACK "+npc, "OK {")
		if strings.Contains(got, `"status":"victory"`) {
			return turn
		}
		if strings.Contains(got, `"status":"respawn"`) {
			test.Fatalf("knocked out by %s: %s", npc, got)
		}
	}
	test.Fatalf("%s never died", npc)
	return 0
}

func walk(client *peer, dirs ...string) {
	client.test.Helper()
	for _, direction := range dirs {
		client.check("MOVE "+direction, "OK room=")
	}
}

// waitFor reads raw lines until one contains want (events are asynchronous).
func waitFor(test *testing.T, client *peer, want string) {
	test.Helper()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if strings.Contains(client.next(), want) {
			return
		}
	}
	test.Fatalf("never received %q", want)
}

// TestStorylineCanBeWon plays the whole main story (and one side quest).
func TestStorylineCanBeWon(test *testing.T) {
	srv, addr := launch(test)
	srv.mu.Lock()
	srv.rateLimit = 10000 // the test plays much faster than a human
	srv.mu.Unlock()
	watcher := join(test, addr, "watcher")
	hero := join(test, addr, "hero")

	// Chapters are locked until their prerequisites are done; TALK gives hints.
	hero.check("QUEST City Guard", "ERR 406 NO_QUEST_AVAILABLE")
	hero.check("TALK City Guard", "OK Keep the peace")
	hero.check("TALK Master Cartographer", "OK Before we chase")

	// The forge gate needs the Copper Key from the tavern.
	walk(hero, "north")
	hero.check("MOVE north", "ERR 302 EXIT_LOCKED")
	walk(hero, "south", "south")
	hero.check("TAKE Copper Key", "OK taken=item.copper_key")
	walk(hero, "north")
	hero.check("QUEST Master Cartographer", "OK {")
	walk(hero, "north", "north")
	hero.check("TAKE Iron Shield", "OK taken=item.iron_shield")
	hero.check("TALK Ghost Smith", "OK Clang")
	hero.check("QUEST Ghost Smith", "ERR 406 NO_QUEST_AVAILABLE")

	// Chapter 1: deliver the compass. The consumed compass returns to the library.
	walk(hero, "south", "east")
	hero.check("TAKE Silver Compass", "OK taken=item.silver_compass")
	walk(hero, "east")
	hero.check("TAKE Rusty Sword", "OK taken=item.rusty_sword")
	hero.check("QUEST Marsh Ranger", "ERR 406 NO_QUEST_AVAILABLE")
	walk(hero, "west", "west", "south")
	hero.check("TALK Master Cartographer", "OK Thank you!")
	hero.check("TAKE Old Map Fragment", "OK taken=item.map_fragment")
	walk(hero, "north", "east")
	if look := hero.check("LOOK", "OK {"); !strings.Contains(look, "item.silver_compass") {
		test.Fatalf("compass did not return to the library: %s", look)
	}

	// Side quest: the notes give a permanent +3 attack.
	hero.check("QUEST Old Librarian", "OK {")
	hero.check("TALK Old Librarian", "OK Thank you!")

	// Chapter 2: the wraith.
	walk(hero, "east")
	hero.check("QUEST Marsh Ranger", "OK {")
	walk(hero, "south", "south")
	fight(test, hero, "Marsh Wraith")

	// Chapter 3: the bandit drops the Star Lens.
	walk(hero, "north", "north", "west", "west", "south")
	hero.check("QUEST City Guard", "OK {")
	walk(hero, "north", "east", "east", "north")
	hero.check("MOVE north", "ERR 302 EXIT_LOCKED")
	fight(test, hero, "Ruin Bandit")
	if look := hero.check("LOOK", "OK {"); !strings.Contains(look, "item.star_lens") {
		test.Fatalf("bandit dropped no lens: %s", look)
	}
	hero.check("TAKE Star Lens", "OK taken=item.star_lens")
	walk(hero, "north") // the lens opens the sanctum
	hero.check("ATTACK Eclipse Warden", "ERR 405 NPC_INVULNERABLE")

	// Chapter 4: starsteel (+8 attack). Sword gone, so 14 + 3 (notes) + 8 = 25.
	walk(hero, "south", "south", "west", "west", "north")
	hero.check("QUEST Ghost Smith", "OK {")
	hero.check("TALK Ghost Smith", "OK Thank you!")
	if st := hero.check("STATUS", "OK {"); !strings.Contains(st, `"attack":25`) || !strings.Contains(st, `"defense":4`) {
		test.Fatalf("unexpected stats: %s", st)
	}

	// Chapter 5: the Warden drops the Heart of Time.
	walk(hero, "south", "east", "east")
	hero.check("QUEST Marsh Ranger", "OK {")
	walk(hero, "north", "north") // door stays open for this player
	fight(test, hero, "Eclipse Warden")
	hero.check("TAKE Heart of Time", "OK taken=item.heart_of_time")

	// Chapter 6: bring the Heart back and win.
	walk(hero, "south", "south", "west", "west", "south")
	hero.check("QUEST Master Cartographer", "OK {")
	hero.check("TALK Master Cartographer", "OK Thank you!")
	if st := hero.check("STATUS", "OK {"); !strings.Contains(st, `"victory":true`) {
		test.Fatalf("no victory: %s", st)
	}
	if journal := hero.check("QUESTS", "OK ["); strings.Count(journal, `"status":"completed"`) != 7 {
		test.Fatalf("journal: %s", journal)
	}
	hero.check("QUEST Master Cartographer", "ERR 406 NO_QUEST_AVAILABLE")
	hero.check("TALK Master Cartographer", "OK Tick, tock")
	waitFor(test, watcher, "EVT GLOBAL VICTORY hero")
}

func TestUseItemsAndStoryIntro(test *testing.T) {
	_, addr := launch(test)
	conn := join(test, addr, "healer")
	// The intro event follows the CONNECT reply.
	waitFor(test, conn, "EVT STORY INTRO At midnight")
	conn.check("TAKE Old Map Fragment", "OK taken=")
	conn.check("USE Old Map Fragment", "ERR 400 ITEM_NOT_USABLE")
	conn.check("USE Healing Herbs", "ERR 404 ITEM_NOT_IN_INVENTORY")
	walk(conn, "east")
	conn.check("TAKE Healing Herbs", "OK taken=item.herbs")
	walk(conn, "east")
	fight(test, conn, "Shadow Wolf") // 30 HP: 3 hits, 2 counters of 7
	got := conn.check("USE herbs", "OK {")
	if !strings.Contains(got, `"healed":14`) || !strings.Contains(got, `"hp":100`) {
		test.Fatalf("use: %s", got)
	}
	conn.check("INVENTORY", `OK ["item.map_fragment"]`)
	conn.check("ATTACK City Guard", "ERR 404 NPC_NOT_FOUND")
}
