package narrator

import (
	"path/filepath"
	"strings"
	"testing"

	"tap/internal/world"
)

func catalog(test *testing.T) *world.Data {
	test.Helper()
	data := LoadCatalog(filepath.Join("..", "..", "world", "world.json"))
	if data == nil {
		test.Fatal("catalog not loaded")
	}
	return data
}

// step sends a command and checks the narration of its reply.
func step(test *testing.T, narrator *Narrator, command, reply, want string) {
	test.Helper()
	if command != "" {
		narrator.Expect(command, false)
	}
	got, _ := narrator.Narrate(reply)
	if !strings.Contains(got, want) {
		test.Fatalf("%q / %q => %q, want it to contain %q", command, reply, got, want)
	}
}

func TestRepliesInEnglish(test *testing.T) {
	narrator := New(catalog(test), "")
	step(test, narrator, "", "OK hello proto=1", "gates of the shared world")
	step(test, narrator, "CONNECT alice", "OK connected", "Welcome, alice!")
	step(test, narrator, "MOVE north", "OK room=loc.market", "You head north and arrive at Moonlight Market.")
	step(test, narrator, "TAKE silver compass", "OK taken=item.silver_compass", "You pick up the Silver Compass.")
	step(test, narrator, "DROP item.silver_compass", "OK dropped=item.silver_compass", "You drop the Silver Compass.")
	step(test, narrator, "INVENTORY", `OK ["item.copper_key","item.herbs"]`, "You are carrying: Copper Key and Healing Herbs.")
	step(test, narrator, "INVENTORY", `OK []`, "Your inventory is empty.")
	step(test, narrator, "TALK cartographer", "OK Bring me the compass.", `Master Cartographer says: "Bring me the compass."`)
	step(test, narrator, "ATTACK Marsh Wraith", `OK {"attacker_hp":91,"counter_damage":9,"damage":14,"status":"combat","target_hp":21}`, "You strike the Marsh Wraith for 14 damage (21 HP left). It hits back for 9 damage; you have 91 HP.")
	step(test, narrator, "ATTACK npc.wraith", `OK {"attacker_hp":91,"counter_damage":0,"damage":14,"status":"victory","target_hp":0}`, "defeat it!")
	step(test, narrator, "DEFEND", `OK {"damage_taken":5,"defended":true,"hp":80,"status":"combat"}`, "take only 5 damage")
	step(test, narrator, "STATUS", `OK {"gold":25,"hp":80,"max_hp":100,"status":"healthy"}`, "You have 80/100 HP and you are healthy. Gold: 25.")
	step(test, narrator, "WHO", "OK players=3", "There are 3 players online.")
	step(test, narrator, "QUEST Marsh Ranger", `OK {"description":"Defeat it.","name":"The Marsh Wraith","quest_id":"quest.wraith","reward":"50 gold, 20 HP","status":"active"}`, `Quest "The Marsh Wraith" is active. Defeat it. Reward: 50 gold, 20 HP.`)
	step(test, narrator, "QUESTS", `OK [{"name":"A True North","progress":"1/1","quest_id":"quest.compass","status":"completed"}]`, "Quest journal: A True North (completed, 1/1).")
	step(test, narrator, "GROUP INVITE bob", "OK", "You invited bob to your group.")
	step(test, narrator, "QUIT", "OK bye", "Goodbye!")
}

func TestErrorsInEnglish(test *testing.T) {
	narrator := New(catalog(test), "alice")
	narrator.SetGreeted()
	step(test, narrator, "MOVE up", "ERR 301 NO_EXIT", `You can't go "up" from here.`)
	step(test, narrator, "TAKE unicorn", "ERR 404 ITEM_NOT_FOUND", `There is no "unicorn" here`)
	step(test, narrator, "ATTACK guard", "ERR 405 NPC_NOT_HOSTILE", "The City Guard is not hostile")
	step(test, narrator, "CHAT GROUP hi", "ERR 401 NOT_IN_GROUP", "You are not in a group.")
	step(test, narrator, "FOO", "ERR 400 UNKNOWN_COMMAND", `Unknown command "FOO".`)
	step(test, narrator, "BAR", "ERR 499 SOMETHING_ODD", "Error 499: something odd.")
}

func TestEventsAndQuietCommands(test *testing.T) {
	narrator := New(catalog(test), "alice")
	narrator.SetGreeted()
	// A quiet refresh is consumed but not narrated, and does not shift later replies.
	narrator.Expect("LOOK", true)
	narrator.Expect("MOVE east", false)
	if text, ok := narrator.Narrate(`OK {"room":{"id":"loc.square"}}`); ok {
		test.Fatalf("quiet command narrated: %q", text)
	}
	step(test, narrator, "", "EVT ROOM PRESENCE ENTER bob", "bob entered the room.")
	step(test, narrator, "", "OK room=loc.garden", "You head east and arrive at Glass Garden.")
	step(test, narrator, "", "EVT ROOM ITEM TAKE bob item.herbs", "bob picked up the Healing Herbs.")
	step(test, narrator, "", "EVT GLOBAL CHAT bob Hello 世界", "bob says to everyone: Hello 世界")
	step(test, narrator, "", "EVT ROOM CHAT alice hi", "You say to the room: hi")
	step(test, narrator, "", "EVT GROUP INVITE bob", "bob invited you to their group. Type GROUP JOIN bob to accept.")
	step(test, narrator, "", "EVT ROOM COMBAT bob npc.wraith damage=14 counter_damage=0 target_hp=0 status=victory", "bob strikes the Marsh Wraith for 14 damage and defeats it!")
	step(test, narrator, "", "EVT QUEST COMPLETE quest.compass", `Quest complete: "A True North"! You earned 25 gold and 10 HP.`)
	step(test, narrator, "", "EVT PLAYER RESPAWN room=loc.square hp=35", "You wake up in Clockwork Square with 35 HP.")
	step(test, narrator, "", "EVT STATS players=2", "There are now 2 players online.")
	// Your own actions are already narrated by the reply: no duplicate event message.
	for _, line := range []string{"EVT ROOM PRESENCE ENTER alice", "EVT ROOM ITEM DROP Alice item.herbs", "EVT ROOM COMBAT alice DEFEND damage_taken=5"} {
		if text, ok := narrator.Narrate(line); ok {
			test.Fatalf("%q narrated as %q", line, text)
		}
	}
}

func TestWorksWithoutCatalog(test *testing.T) {
	narrator := New(nil, "")
	narrator.SetGreeted()
	step(test, narrator, "TAKE item.loaf_bread", "OK taken=item.loaf_bread", "You pick up the loaf bread.")
	step(test, narrator, "", "EVT ROOM NPC RESPAWN npc.goblin", "The goblin has returned!")
}

func TestStorylineMessages(test *testing.T) {
	narrator := New(catalog(test), "")
	narrator.SetGreeted()
	step(test, narrator, "CONNECT hero", "OK connected", "Welcome, hero!")
	step(test, narrator, "", "EVT STORY INTRO At midnight the clock stopped.", "📜 At midnight the clock stopped.")
	step(test, narrator, "MOVE north", "OK room=loc.market", "Moonlight Market")
	step(test, narrator, "MOVE north", "ERR 302 EXIT_LOCKED", "The way north is locked. You need the Copper Key to open it.")
	step(test, narrator, "", "EVT PLAYER UNLOCK north item.star_lens", "You use the Star Lens and the way north opens.")
	step(test, narrator, "ATTACK warden", "ERR 405 NPC_INVULNERABLE", `Complete the quest "Starsteel"`)
	step(test, narrator, "USE herbs", `OK {"counter_damage":12,"healed":35,"hp":70,"used":"item.herbs"}`, "You use the Healing Herbs and recover 35 HP (now 70 HP). Your enemy takes the chance to hit you for 12 damage.")
	step(test, narrator, "USE lantern", "ERR 400 ITEM_NOT_USABLE", "You can't use the lantern.")
	step(test, narrator, "", "EVT ROOM ITEM LOOT npc.bandit item.star_lens", "The Ruin Bandit drops the Star Lens!")
	step(test, narrator, "", "EVT ROOM ITEM RESPAWN item.silver_compass", "A Silver Compass appears here.")
	step(test, narrator, "STATUS", `OK {"hp":90,"max_hp":100,"status":"healthy","gold":10,"attack":25,"defense":4,"victory":true}`, "Attack: 25, defense: 4. You have won the game")
	step(test, narrator, "", "EVT GLOBAL VICTORY bob", "🏆 bob completed the final quest and won the game!")
	step(test, narrator, "", "EVT GLOBAL VICTORY hero", "🏆 The Heart of Time beats again!")
	step(test, narrator, "QUESTS", `OK [{"quest_id":"quest.wraith","name":"The Marsh Wraith","status":"active","progress":"0/1","description":"Defeat the wraith."}]`, "The Marsh Wraith (active, 0/1) - Defeat the wraith.")
}
