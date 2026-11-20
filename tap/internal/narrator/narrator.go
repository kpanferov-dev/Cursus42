// Package narrator turns raw TAP protocol lines (OK / ERR / EVT) into
// human-readable English sentences. It is used by both the CLI and the GUI
// bridge so that every action produces the same "activity chat" message.
//
// The narrator is purely client-side: it never changes what is sent on the
// wire, so it also works against other teams' RFC 42TAP servers. Replies are
// matched to commands in FIFO order (each TAP command produces exactly one
// OK/ERR reply, while EVT lines are asynchronous and never consume a command).
package narrator

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
	"sync"

	"tap/internal/world"
)

type pending struct {
	line  string
	quiet bool
}

// Narrator keeps the minimum client state needed to describe replies:
// the player's own name and the queue of commands awaiting a reply.
type Narrator struct {
	mu      sync.Mutex
	cat     *world.Data
	self    string
	greeted bool
	pending []pending
	where   string // current room, to explain locked exits
}

// New creates a narrator. catalog may be nil (IDs are then humanized).
// self is the player's name if already known (GUI bridge), or "" (CLI).
func New(catalog *world.Data, self string) *Narrator {
	return &Narrator{cat: catalog, self: self}
}

// LoadCatalog reads a world JSON file for display names only. It does not
// validate the world and returns nil if the file is missing or unreadable,
// so a client can still talk to servers with a different world.
func LoadCatalog(path string) *world.Data {
	content, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	var data world.Data
	if json.Unmarshal(content, &data) != nil {
		return nil
	}
	return &data
}

// SetGreeted marks the "OK hello" greeting as already consumed.
func (narrator *Narrator) SetGreeted() {
	narrator.mu.Lock()
	narrator.greeted = true
	narrator.mu.Unlock()
}

// Expect registers a command that was (or is about to be) sent to the server.
// Quiet commands (automatic GUI refreshes) are tracked but not narrated.
func (narrator *Narrator) Expect(line string, quiet bool) {
	narrator.mu.Lock()
	defer narrator.mu.Unlock()
	narrator.pending = append(narrator.pending, pending{strings.TrimSpace(line), quiet})
}

// Cancel removes the most recently registered command (used when sending fails).
func (narrator *Narrator) Cancel() {
	narrator.mu.Lock()
	defer narrator.mu.Unlock()
	if len(narrator.pending) > 0 {
		narrator.pending = narrator.pending[:len(narrator.pending)-1]
	}
}

// Narrate returns the English description of one server line. ok is false
// when the line should not produce an activity message.
func (narrator *Narrator) Narrate(line string) (text string, ok bool) {
	text, ok, _ = narrator.Describe(line)
	return text, ok
}

// Describe is Narrate plus quiet: true when the line is the reply to a quiet
// (automatic) command, so a client can also hide the raw line.
func (narrator *Narrator) Describe(line string) (text string, ok, quiet bool) {
	line = strings.TrimSpace(line)
	if line == "" {
		return "", false, false
	}
	narrator.mu.Lock()
	defer narrator.mu.Unlock()
	if !narrator.greeted && strings.HasPrefix(line, "OK hello") {
		narrator.greeted = true
		return "You reach the gates of the shared world (TAP protocol " + strings.TrimPrefix(line, "OK hello proto=") + ").", true, false
	}
	narrator.trackRoom(line)
	if strings.HasPrefix(line, "EVT ") {
		text = narrator.event(strings.TrimPrefix(line, "EVT "))
		return text, text != "", false
	}
	if line != "OK" && !strings.HasPrefix(line, "OK ") && !strings.HasPrefix(line, "ERR ") {
		return "", false, false
	}
	if strings.HasPrefix(line, "ERR 900") {
		// Connection-level failure: not a reply to a specific command.
		return "The connection to the server failed.", true, false
	}
	cmd := pending{}
	if len(narrator.pending) > 0 {
		cmd = narrator.pending[0]
		narrator.pending = narrator.pending[1:]
	}
	if cmd.quiet {
		return "", false, true
	}
	if strings.HasPrefix(line, "ERR ") {
		text = narrator.failure(cmd.line, strings.TrimPrefix(line, "ERR "))
	} else {
		text = narrator.success(cmd.line, strings.TrimSpace(strings.TrimPrefix(line, "OK")))
	}
	return text, text != "", false
}

// trackRoom follows the player's room from MOVE/FLEE, LOOK and respawn lines.
func (narrator *Narrator) trackRoom(line string) {
	switch {
	case line == "OK connected" && narrator.cat != nil:
		narrator.where = narrator.cat.Start
	case strings.HasPrefix(line, "OK room="):
		narrator.where = strings.TrimPrefix(line, "OK room=")
	case strings.HasPrefix(line, "EVT PLAYER RESPAWN "):
		if room := keyValues(strings.Fields(line))["room"]; room != "" {
			narrator.where = room
		}
	case strings.HasPrefix(line, "OK {\"") && strings.Contains(line, `"room":{`):
		var look struct {
			Room struct {
				ID string `json:"id"`
			} `json:"room"`
		}
		if json.Unmarshal([]byte(line[3:]), &look) == nil && look.Room.ID != "" {
			narrator.where = look.Room.ID
		}
	}
}

// ---------------------------------------------------------------- replies

func splitCommand(line string) (cmd, arg string) {
	cmd, arg, _ = strings.Cut(strings.TrimSpace(line), " ")
	return strings.ToUpper(cmd), strings.TrimSpace(arg)
}

func (narrator *Narrator) success(command, data string) string {
	cmd, arg := splitCommand(command)
	switch cmd {
	case "CONNECT":
		if data == "connected" {
			narrator.self = arg
			return fmt.Sprintf("Welcome, %s! You have entered the shared world.", arg)
		}
	case "LOOK":
		return narrator.look(data)
	case "MOVE":
		if room, ok := strings.CutPrefix(data, "room="); ok {
			return fmt.Sprintf("You head %s and arrive at %s.", strings.ToLower(arg), narrator.room(room))
		}
	case "FLEE":
		if room, ok := strings.CutPrefix(data, "room="); ok {
			return fmt.Sprintf("You flee from combat and run back to %s.", narrator.room(room))
		}
	case "TAKE":
		if id, ok := strings.CutPrefix(data, "taken="); ok {
			return fmt.Sprintf("You pick up the %s.", narrator.item(id))
		}
	case "DROP":
		if id, ok := strings.CutPrefix(data, "dropped="); ok {
			return fmt.Sprintf("You drop the %s.", narrator.item(id))
		}
	case "INVENTORY":
		var ids []string
		if json.Unmarshal([]byte(data), &ids) == nil {
			if len(ids) == 0 {
				return "Your inventory is empty."
			}
			return "You are carrying: " + listOf(narrator.items(ids)) + "."
		}
	case "TALK":
		return fmt.Sprintf("%s says: \"%s\"", narrator.npcFromArg(arg), data)
	case "ATTACK":
		return narrator.attack(arg, data)
	case "USE":
		var useReply struct {
			Used    string `json:"used"`
			Healed  int    `json:"healed"`
			HP      int    `json:"hp"`
			Counter int    `json:"counter_damage"`
		}
		if json.Unmarshal([]byte(data), &useReply) == nil {
			text := fmt.Sprintf("You use the %s and recover %d HP (now %d HP).", narrator.item(useReply.Used), useReply.Healed, useReply.HP)
			if useReply.Counter > 0 {
				text += fmt.Sprintf(" Your enemy takes the chance to hit you for %d damage.", useReply.Counter)
			}
			return text
		}
	case "DEFEND":
		var defendReply struct {
			HP     int `json:"hp"`
			Damage int `json:"damage_taken"`
		}
		if json.Unmarshal([]byte(data), &defendReply) == nil {
			return fmt.Sprintf("You raise your guard and take only %d damage. You have %d HP left.", defendReply.Damage, defendReply.HP)
		}
	case "STATUS":
		var statusReply struct {
			HP      int    `json:"hp"`
			MaxHP   int    `json:"max_hp"`
			Status  string `json:"status"`
			Gold    *int   `json:"gold"`
			Attack  *int   `json:"attack"`
			Defense *int   `json:"defense"`
			Victory bool   `json:"victory"`
		}
		if json.Unmarshal([]byte(data), &statusReply) == nil {
			text := fmt.Sprintf("You have %d/%d HP and you are %s.", statusReply.HP, statusReply.MaxHP, statusReply.Status)
			if statusReply.Status == "combat" {
				text = fmt.Sprintf("You have %d/%d HP and you are in combat.", statusReply.HP, statusReply.MaxHP)
			}
			if statusReply.Gold != nil {
				text += fmt.Sprintf(" Gold: %d.", *statusReply.Gold)
			}
			if statusReply.Attack != nil && statusReply.Defense != nil {
				text += fmt.Sprintf(" Attack: %d, defense: %d.", *statusReply.Attack, *statusReply.Defense)
			}
			if statusReply.Victory {
				text += " You have won the game: the Great Clock ticks again thanks to you!"
			}
			return text
		}
	case "WHO":
		if count, ok := strings.CutPrefix(data, "players="); ok {
			if count == "1" {
				return "You are the only player online."
			}
			return fmt.Sprintf("There are %s players online.", count)
		}
	case "QUEST":
		var questReply struct {
			ID          string `json:"quest_id"`
			Name        string `json:"name"`
			Description string `json:"description"`
			Reward      string `json:"reward"`
			Status      string `json:"status"`
		}
		if json.Unmarshal([]byte(data), &questReply) == nil {
			name := firstNonEmpty(questReply.Name, questReply.ID)
			text := fmt.Sprintf("Quest \"%s\" is %s.", name, questReply.Status)
			if questReply.Status == "active" {
				text = fmt.Sprintf("Quest \"%s\" is active.", name)
			}
			if questReply.Description != "" {
				text += " " + questReply.Description
			}
			if questReply.Reward != "" {
				text += " Reward: " + questReply.Reward + "."
			}
			return text
		}
	case "QUESTS":
		var list []struct {
			ID          string `json:"quest_id"`
			Name        string `json:"name"`
			Status      string `json:"status"`
			Progress    string `json:"progress"`
			Description string `json:"description"`
		}
		if json.Unmarshal([]byte(data), &list) == nil {
			if len(list) == 0 {
				return "Your quest journal is empty. Use QUEST <npc> to accept a quest."
			}
			parts := make([]string, 0, len(list))
			for _, listed := range list {
				name := firstNonEmpty(listed.Name, narrator.quest(listed.ID))
				progressText := listed.Status
				if listed.Progress != "" {
					progressText += ", " + listed.Progress
				}
				entry := fmt.Sprintf("%s (%s)", name, progressText)
				if listed.Status == "active" && listed.Description != "" {
					entry += " - " + listed.Description
				}
				parts = append(parts, entry)
			}
			return "Quest journal: " + strings.Join(parts, "; ") + "."
		}
	case "CHAT":
		// The server echoes the message back as an EVT; that event is narrated instead.
		return ""
	case "GROUP":
		sub, rest := splitCommand(arg)
		switch sub {
		case "CREATE":
			return fmt.Sprintf("You created a new group (%s). Invite players with GROUP INVITE <name>.", strings.TrimPrefix(data, "group="))
		case "INVITE":
			return fmt.Sprintf("You invited %s to your group.", rest)
		case "JOIN":
			return fmt.Sprintf("You joined %s's group.", rest)
		case "LEAVE":
			return "You left your group."
		}
	case "QUIT":
		if data == "bye" {
			return "Goodbye! You have left the world."
		}
	}
	if data == "" {
		return "Done."
	}
	return "Server: " + data
}

func (narrator *Narrator) look(data string) string {
	var lookReply struct {
		Room struct {
			ID          string            `json:"id"`
			Name        string            `json:"name"`
			Description string            `json:"description"`
			Exits       map[string]string `json:"exits"`
		} `json:"room"`
		Players []string `json:"players"`
		Items   []string `json:"items"`
		NPCs    []string `json:"npcs"`
	}
	if json.Unmarshal([]byte(data), &lookReply) != nil {
		return "Server: " + data
	}
	var builder strings.Builder
	fmt.Fprintf(&builder, "You are in %s.", firstNonEmpty(lookReply.Room.Name, narrator.room(lookReply.Room.ID)))
	if lookReply.Room.Description != "" {
		builder.WriteString(" " + lookReply.Room.Description)
	}
	dirs := make([]string, 0, len(lookReply.Room.Exits))
	for dir := range lookReply.Room.Exits {
		dirs = append(dirs, dir)
	}
	sort.Slice(dirs, func(left, right int) bool { return dirRank(dirs[left]) < dirRank(dirs[right]) })
	exits := make([]string, 0, len(dirs))
	for _, dir := range dirs {
		exits = append(exits, fmt.Sprintf("%s to %s", dir, narrator.room(lookReply.Room.Exits[dir])))
	}
	if len(exits) > 0 {
		builder.WriteString(" Exits: " + listOf(exits) + ".")
	} else {
		builder.WriteString(" There are no exits.")
	}
	if len(lookReply.Items) > 0 {
		builder.WriteString(" You see: " + listOf(narrator.items(lookReply.Items)) + ".")
	}
	if len(lookReply.NPCs) > 0 {
		names := make([]string, 0, len(lookReply.NPCs))
		for _, id := range lookReply.NPCs {
			names = append(names, narrator.npc(id))
		}
		builder.WriteString(" Characters here: " + listOf(names) + ".")
	}
	others := []string{}
	for _, player := range lookReply.Players {
		if !strings.EqualFold(player, narrator.self) {
			others = append(others, player)
		}
	}
	if len(others) > 0 {
		builder.WriteString(" Other players here: " + listOf(others) + ".")
	}
	return builder.String()
}

func (narrator *Narrator) attack(arg, data string) string {
	var attackReply struct {
		AttackerHP int    `json:"attacker_hp"`
		TargetHP   int    `json:"target_hp"`
		Damage     int    `json:"damage"`
		Counter    int    `json:"counter_damage"`
		Status     string `json:"status"`
	}
	if json.Unmarshal([]byte(data), &attackReply) != nil {
		return "Server: " + data
	}
	target := narrator.npcFromArg(arg)
	switch attackReply.Status {
	case "victory":
		return fmt.Sprintf("You strike the %s for %d damage and defeat it!", target, attackReply.Damage)
	case "respawn":
		return fmt.Sprintf("You strike the %s for %d damage (%d HP left), but its counterattack of %d knocks you out!", target, attackReply.Damage, attackReply.TargetHP, attackReply.Counter)
	}
	return fmt.Sprintf("You strike the %s for %d damage (%d HP left). It hits back for %d damage; you have %d HP.", target, attackReply.Damage, attackReply.TargetHP, attackReply.Counter, attackReply.AttackerHP)
}

func (narrator *Narrator) failure(command, rest string) string {
	cmd, arg := splitCommand(command)
	code, reason, _ := strings.Cut(rest, " ")
	reason = strings.TrimSpace(reason)
	switch reason {
	case "NAME_IN_USE":
		return fmt.Sprintf("The name \"%s\" is already taken. Please choose another one.", arg)
	case "INVALID_USERNAME":
		return "Invalid username: use 1-32 letters, digits, '_' or '-' (no spaces)."
	case "ALREADY_CONNECTED":
		return "You are already connected."
	case "AUTH_REQUIRED":
		return "You must CONNECT with a username first."
	case "EXIT_LOCKED":
		if narrator.cat != nil {
			if key := narrator.cat.Rooms[narrator.where].Locks[strings.ToLower(arg)]; key != "" {
				return fmt.Sprintf("The way %s is locked. You need the %s to open it.", strings.ToLower(arg), narrator.item(key))
			}
		}
		return fmt.Sprintf("The way %s is locked. You need a special item to open it.", strings.ToLower(arg))
	case "NPC_INVULNERABLE":
		target := narrator.npcFromArg(arg)
		if narrator.cat != nil {
			for _, character := range narrator.cat.NPCs {
				if character.Name == target && character.RequiresQuest != "" {
					return fmt.Sprintf("Your blows pass straight through the %s! Complete the quest \"%s\" to be able to hurt it.", target, narrator.quest(character.RequiresQuest))
				}
			}
		}
		return fmt.Sprintf("Your blows can't harm the %s yet. You need to grow stronger first.", target)
	case "ITEM_NOT_USABLE":
		return fmt.Sprintf("You can't use the %s. Only healing items can be used.", arg)
	case "NO_EXIT":
		return fmt.Sprintf("You can't go \"%s\" from here.", arg)
	case "IN_COMBAT_USE_FLEE":
		return "You are in combat and can't simply walk away. Use FLEE to escape."
	case "ITEM_NOT_FOUND":
		return fmt.Sprintf("There is no \"%s\" here that you can take.", arg)
	case "ITEM_NOT_IN_INVENTORY":
		return fmt.Sprintf("You are not carrying \"%s\".", arg)
	case "INVENTORY_FULL":
		return "Your inventory is full. Drop something first."
	case "NPC_NOT_FOUND":
		return fmt.Sprintf("There is nobody called \"%s\" here.", arg)
	case "NPC_NOT_HOSTILE":
		return fmt.Sprintf("The %s is not hostile; you can't attack them.", narrator.npcFromArg(arg))
	case "ALREADY_IN_COMBAT":
		return "You are already fighting someone else. Finish that fight or FLEE first."
	case "NOT_IN_COMBAT":
		return "You are not in combat."
	case "NO_QUEST_AVAILABLE":
		return fmt.Sprintf("The %s has no quest for you right now. TALK to them for a hint.", narrator.npcFromArg(arg))
	case "NOT_IN_GROUP":
		return "You are not in a group."
	case "ALREADY_IN_GROUP":
		if strings.HasPrefix(strings.ToUpper(arg), "INVITE") {
			return "That player already belongs to a group."
		}
		return "You already belong to a group."
	case "PLAYER_NOT_FOUND":
		return "That player is not online."
	case "GROUP_NOT_FOUND":
		return "That player is not leading a group."
	case "INVITE_REQUIRED":
		return "You need an invitation from the group leader before joining."
	case "INVALID_SCOPE":
		return "Unknown chat scope. Use GLOBAL, ROOM or GROUP."
	case "UNKNOWN_COMMAND":
		return fmt.Sprintf("Unknown command \"%s\".", strings.ToUpper(cmd))
	case "BAD_REQUEST":
		return fmt.Sprintf("The command \"%s\" is malformed or has invalid arguments.", strings.TrimSpace(command))
	case "RATE_LIMITED":
		return "Slow down! You are sending commands too fast."
	case "SEND_FAILED":
		return "Your command could not be sent to the server."
	}
	words := strings.ToLower(strings.ReplaceAll(reason, "_", " "))
	if words == "" {
		return "Error " + code + "."
	}
	return fmt.Sprintf("Error %s: %s.", code, words)
}

// ---------------------------------------------------------------- events

func (narrator *Narrator) isSelf(name string) bool {
	return narrator.self != "" && strings.EqualFold(name, narrator.self)
}

func (narrator *Narrator) event(body string) string {
	switch {
	case strings.HasPrefix(body, "ROOM PRESENCE ENTER "):
		who := strings.TrimPrefix(body, "ROOM PRESENCE ENTER ")
		if narrator.isSelf(who) {
			return ""
		}
		return who + " entered the room."
	case strings.HasPrefix(body, "ROOM PRESENCE LEAVE "):
		who := strings.TrimPrefix(body, "ROOM PRESENCE LEAVE ")
		if narrator.isSelf(who) {
			return ""
		}
		return who + " left the room."
	case strings.HasPrefix(body, "ROOM CHAT "):
		return narrator.chat("to the room", strings.TrimPrefix(body, "ROOM CHAT "))
	case strings.HasPrefix(body, "GLOBAL CHAT "):
		return narrator.chat("to everyone", strings.TrimPrefix(body, "GLOBAL CHAT "))
	case strings.HasPrefix(body, "GROUP CHAT "):
		return narrator.chat("to the group", strings.TrimPrefix(body, "GROUP CHAT "))
	case strings.HasPrefix(body, "GROUP INVITE "):
		leader := strings.TrimPrefix(body, "GROUP INVITE ")
		return fmt.Sprintf("%s invited you to their group. Type GROUP JOIN %s to accept.", leader, leader)
	case strings.HasPrefix(body, "GROUP JOIN "):
		who := strings.TrimPrefix(body, "GROUP JOIN ")
		if narrator.isSelf(who) {
			return ""
		}
		return who + " joined your group."
	case strings.HasPrefix(body, "GROUP LEAVE "):
		return strings.TrimPrefix(body, "GROUP LEAVE ") + " left your group."
	case strings.HasPrefix(body, "STATS players="):
		count := strings.TrimPrefix(body, "STATS players=")
		if count == "1" {
			return "There is now 1 player online."
		}
		return "There are now " + count + " players online."
	case strings.HasPrefix(body, "STORY INTRO "):
		return "📜 " + strings.TrimPrefix(body, "STORY INTRO ")
	case strings.HasPrefix(body, "GLOBAL VICTORY "):
		who := strings.TrimPrefix(body, "GLOBAL VICTORY ")
		if narrator.isSelf(who) {
			if narrator.cat != nil && narrator.cat.Story.Victory != "" {
				return "🏆 " + narrator.cat.Story.Victory
			}
			return "🏆 You completed the final quest and won the game!"
		}
		return "🏆 " + who + " completed the final quest and won the game!"
	case strings.HasPrefix(body, "ROOM ITEM RESPAWN "):
		return fmt.Sprintf("A %s appears here.", narrator.item(strings.TrimPrefix(body, "ROOM ITEM RESPAWN ")))
	case strings.HasPrefix(body, "ROOM ITEM LOOT "):
		fields := strings.Fields(body)
		if len(fields) >= 5 {
			return fmt.Sprintf("The %s drops the %s!", narrator.npc(fields[3]), narrator.item(fields[4]))
		}
	case strings.HasPrefix(body, "PLAYER UNLOCK "):
		fields := strings.Fields(body)
		if len(fields) >= 4 {
			return fmt.Sprintf("You use the %s and the way %s opens.", narrator.item(fields[3]), fields[2])
		}
	case strings.HasPrefix(body, "ROOM ITEM TAKE "), strings.HasPrefix(body, "ROOM ITEM DROP "):
		fields := strings.Fields(body)
		if len(fields) < 5 || narrator.isSelf(fields[3]) {
			return ""
		}
		verb := "picked up"
		if fields[2] == "DROP" {
			verb = "dropped"
		}
		return fmt.Sprintf("%s %s the %s.", fields[3], verb, narrator.item(fields[4]))
	case strings.HasPrefix(body, "ROOM NPC RESPAWN "):
		return fmt.Sprintf("The %s has returned!", narrator.npc(strings.TrimPrefix(body, "ROOM NPC RESPAWN ")))
	case strings.HasPrefix(body, "ROOM COMBAT "):
		return narrator.combatEvent(strings.Fields(strings.TrimPrefix(body, "ROOM COMBAT ")))
	case strings.HasPrefix(body, "QUEST COMPLETE "):
		id := strings.TrimPrefix(body, "QUEST COMPLETE ")
		text := fmt.Sprintf("Quest complete: \"%s\"!", narrator.quest(id))
		if narrator.cat != nil {
			if quest, ok := narrator.cat.Quests[id]; ok {
				text += fmt.Sprintf(" You earned %d gold and %d HP.", quest.RewardGold, quest.RewardHP)
			}
		}
		return text
	case strings.HasPrefix(body, "PLAYER RESPAWN"):
		kv := keyValues(strings.Fields(body))
		return fmt.Sprintf("You were defeated! You wake up in %s with %s HP.", narrator.room(kv["room"]), firstNonEmpty(kv["hp"], "?"))
	}
	return "Event: " + body
}

func (narrator *Narrator) chat(scope, rest string) string {
	who, msg, _ := strings.Cut(rest, " ")
	if narrator.isSelf(who) {
		return fmt.Sprintf("You say %s: %s", scope, msg)
	}
	return fmt.Sprintf("%s says %s: %s", who, scope, msg)
}

func (narrator *Narrator) combatEvent(fields []string) string {
	if len(fields) < 2 || narrator.isSelf(fields[0]) {
		return ""
	}
	who, kv := fields[0], keyValues(fields)
	if fields[1] == "DEFEND" {
		return fmt.Sprintf("%s defends and takes %s damage.", who, firstNonEmpty(kv["damage_taken"], "?"))
	}
	target := narrator.npc(fields[1])
	switch kv["status"] {
	case "victory":
		return fmt.Sprintf("%s strikes the %s for %s damage and defeats it!", who, target, kv["damage"])
	case "respawn":
		return fmt.Sprintf("%s strikes the %s but is knocked out by its counterattack!", who, target)
	}
	return fmt.Sprintf("%s strikes the %s for %s damage (%s HP left); it hits back for %s.", who, target, kv["damage"], kv["target_hp"], kv["counter_damage"])
}

// ---------------------------------------------------------------- labels

func humanize(id string) string {
	if _, rest, ok := strings.Cut(id, "."); ok {
		id = rest
	}
	return strings.ReplaceAll(id, "_", " ")
}

func (narrator *Narrator) item(id string) string {
	if narrator.cat != nil {
		if it, ok := narrator.cat.Items[id]; ok && it.Name != "" {
			return it.Name
		}
	}
	return humanize(id)
}

func (narrator *Narrator) items(ids []string) []string {
	out := make([]string, 0, len(ids))
	for _, id := range ids {
		out = append(out, narrator.item(id))
	}
	return out
}

func (narrator *Narrator) npc(id string) string {
	if narrator.cat != nil {
		if character, ok := narrator.cat.NPCs[id]; ok && character.Name != "" {
			return character.Name
		}
	}
	return humanize(id)
}

// npcFromArg resolves what the user typed (ID, short ID or display name).
func (narrator *Narrator) npcFromArg(arg string) string {
	if narrator.cat != nil {
		for id, character := range narrator.cat.NPCs {
			if strings.EqualFold(arg, id) || strings.EqualFold(arg, character.Name) || strings.EqualFold(arg, strings.TrimPrefix(id, "npc.")) {
				return firstNonEmpty(character.Name, humanize(id))
			}
		}
	}
	if strings.HasPrefix(arg, "npc.") {
		return humanize(arg)
	}
	return arg
}

func (narrator *Narrator) room(id string) string {
	if narrator.cat != nil {
		if room, ok := narrator.cat.Rooms[id]; ok && room.Name != "" {
			return room.Name
		}
	}
	return humanize(id)
}

func (narrator *Narrator) quest(id string) string {
	if narrator.cat != nil {
		if quest, ok := narrator.cat.Quests[id]; ok && quest.Name != "" {
			return quest.Name
		}
	}
	return humanize(id)
}

// ---------------------------------------------------------------- helpers

func listOf(parts []string) string {
	switch len(parts) {
	case 0:
		return ""
	case 1:
		return parts[0]
	}
	return strings.Join(parts[:len(parts)-1], ", ") + " and " + parts[len(parts)-1]
}

func dirRank(dir string) int {
	switch dir {
	case "north":
		return 0
	case "east":
		return 1
	case "south":
		return 2
	case "west":
		return 3
	}
	return 4
}

func keyValues(fields []string) map[string]string {
	kv := map[string]string{}
	for _, field := range fields {
		if key, value, ok := strings.Cut(field, "="); ok {
			kv[key] = value
		}
	}
	return kv
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
}
