// Package world loads and validates the static JSON world definition.
package world

import (
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"strings"
	"unicode"
)

type Room struct {
	Name        string            `json:"name"`
	Description string            `json:"description"`
	Exits       map[string]string `json:"exits"`
	Items       []string          `json:"items"`
	NPCs        []string          `json:"npcs"`
	// Map is an optional [x, y] grid position for client maps (y grows southwards).
	Map []int `json:"map,omitempty"`
	// Locks maps an exit direction to the item needed to open it (once per player).
	Locks map[string]string `json:"locks,omitempty"`
}
type Item struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Obtainable  bool   `json:"obtainable"`
	Heal        int    `json:"heal,omitempty"`    // USE restores this much HP (item is consumed)
	Attack      int    `json:"attack,omitempty"`  // weapon bonus while carried (best one counts)
	Defense     int    `json:"defense,omitempty"` // armour bonus while carried (best one counts)
}
type NPC struct {
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Role        string   `json:"role"`
	Dialogue    []string `json:"dialogue"`
	HP          int      `json:"hp"`
	Attack      int      `json:"attack"`
	Quest       string   `json:"quest,omitempty"`  // legacy single quest
	Quests      []string `json:"quests,omitempty"` // quests offered in order
	Loot        string   `json:"loot,omitempty"`   // item dropped when defeated
	// RequiresQuest: the NPC can only be damaged after completing this quest.
	RequiresQuest string `json:"requires_quest,omitempty"`
}

// QuestList returns the quests offered by the NPC, in order.
func (npc NPC) QuestList() []string {
	out := []string{}
	if npc.Quest != "" {
		out = append(out, npc.Quest)
	}
	for _, questID := range npc.Quests {
		if questID != npc.Quest {
			out = append(out, questID)
		}
	}
	return out
}

type Quest struct {
	Name        string `json:"name"`
	Description string `json:"description"`
	Kind        string `json:"kind"`
	Target      string `json:"target"`
	Giver       string `json:"giver"`
	RewardGold  int    `json:"reward_gold"`
	RewardHP    int    `json:"reward_hp"`
	// RewardAttack permanently increases the player's attack.
	RewardAttack int      `json:"reward_attack,omitempty"`
	Requires     []string `json:"requires,omitempty"` // quests to complete first
	Offer        string   `json:"offer,omitempty"`    // TALK text when the quest can be accepted
	Reminder     string   `json:"reminder,omitempty"` // TALK text while the quest is active
	Complete     string   `json:"complete,omitempty"` // TALK text when a delivery completes it
	Final        bool     `json:"final,omitempty"`    // completing it wins the game
}
type Story struct {
	Title   string `json:"title"`
	Intro   string `json:"intro"`
	Victory string `json:"victory"`
}
type Data struct {
	Start  string           `json:"start"`
	Rooms  map[string]Room  `json:"rooms"`
	Items  map[string]Item  `json:"items"`
	NPCs   map[string]NPC   `json:"npcs"`
	Quests map[string]Quest `json:"quests"`
	Story  Story            `json:"story"`
}

func Load(path string) (*Data, error) {
	content, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var data Data
	if err := json.Unmarshal(content, &data); err != nil {
		return nil, fmt.Errorf("parse world: %w", err)
	}
	if err := data.Validate(); err != nil {
		return nil, err
	}
	return &data, nil
}
func (data *Data) Validate() error {
	if _, ok := data.Rooms[data.Start]; !ok {
		return fmt.Errorf("start room %q does not exist", data.Start)
	}
	if len(data.Rooms) < 8 {
		return fmt.Errorf("at least 8 rooms required, got %d", len(data.Rooms))
	}
	usedCells := make(map[[2]int]string)
	for id, room := range data.Rooms {
		if room.Map == nil {
			continue
		}
		if len(room.Map) != 2 {
			return fmt.Errorf("room %s map position must be [x, y]", id)
		}
		cell := [2]int{room.Map[0], room.Map[1]}
		if prev, ok := usedCells[cell]; ok {
			return fmt.Errorf("rooms %s and %s share map position %v", prev, id, room.Map)
		}
		usedCells[cell] = id
	}
	usedItems := make(map[string]string)
	usedNPCs := make(map[string]string)
	for id, room := range data.Rooms {
		if id == "" || room.Name == "" || room.Description == "" {
			return fmt.Errorf("incomplete room %q", id)
		}
		for dir, dest := range room.Exits {
			if _, ok := data.Rooms[dest]; !ok {
				return fmt.Errorf("room %s exit %s references missing %s", id, dir, dest)
			}
			if dir != "north" && dir != "south" && dir != "east" && dir != "west" {
				return fmt.Errorf("invalid direction %s in %s", dir, id)
			}
		}
		for _, itemID := range room.Items {
			if _, ok := data.Items[itemID]; !ok {
				return fmt.Errorf("room %s references unknown item %s", id, itemID)
			}
			if prev, ok := usedItems[itemID]; ok {
				return fmt.Errorf("item %s duplicated in %s and %s", itemID, prev, id)
			}
			usedItems[itemID] = id
		}
		for _, npcID := range room.NPCs {
			if _, ok := data.NPCs[npcID]; !ok {
				return fmt.Errorf("room %s references unknown NPC %s", id, npcID)
			}
			if prev, ok := usedNPCs[npcID]; ok {
				return fmt.Errorf("NPC %s duplicated in %s and %s", npcID, prev, id)
			}
			usedNPCs[npcID] = id
		}
	}
	// All rooms must be reachable from start, irrespective of optional branches.
	visited := map[string]bool{data.Start: true}
	queue := []string{data.Start}
	for len(queue) > 0 {
		room := queue[0]
		queue = queue[1:]
		for _, dest := range data.Rooms[room].Exits {
			if !visited[dest] {
				visited[dest] = true
				queue = append(queue, dest)
			}
		}
	}
	if len(visited) != len(data.Rooms) {
		return fmt.Errorf("world is disconnected: %d of %d rooms reachable", len(visited), len(data.Rooms))
	}
	if len(data.Items) < 4 || len(data.NPCs) < 3 || len(data.Quests) < 2 {
		return fmt.Errorf("world needs 4 items, 3 NPCs, and 2 quests")
	}
	for id, npc := range data.NPCs {
		if npc.HP < 1 || npc.Name == "" {
			return fmt.Errorf("invalid NPC %s", id)
		}
		if _, ok := usedNPCs[id]; !ok {
			return fmt.Errorf("NPC %s has no spawn room", id)
		}
		for _, questID := range npc.QuestList() {
			if _, ok := data.Quests[questID]; !ok {
				return fmt.Errorf("NPC %s points to nonexistent quest %s", id, questID)
			}
		}
		if npc.Loot != "" {
			if _, ok := data.Items[npc.Loot]; !ok {
				return fmt.Errorf("NPC %s drops unknown item %s", id, npc.Loot)
			}
		}
		if npc.RequiresQuest != "" {
			if _, ok := data.Quests[npc.RequiresQuest]; !ok {
				return fmt.Errorf("NPC %s requires unknown quest %s", id, npc.RequiresQuest)
			}
		}
	}
	// An item exists in the world if it spawns in a room or is dropped by an NPC.
	obtainable := func(item string) bool {
		if _, ok := usedItems[item]; ok {
			return true
		}
		for _, npc := range data.NPCs {
			if npc.Loot == item {
				return true
			}
		}
		return false
	}
	for id, it := range data.Items {
		if it.Heal < 0 || it.Attack < 0 || it.Defense < 0 {
			return fmt.Errorf("item %s has negative stats", id)
		}
	}
	for id, room := range data.Rooms {
		for dir, item := range room.Locks {
			if _, ok := room.Exits[dir]; !ok {
				return fmt.Errorf("room %s locks missing exit %s", id, dir)
			}
			if _, ok := data.Items[item]; !ok || !obtainable(item) {
				return fmt.Errorf("room %s lock needs unobtainable item %s", id, item)
			}
		}
	}
	for id, quest := range data.Quests {
		giver, ok := data.NPCs[quest.Giver]
		if !ok || !contains(giver.QuestList(), id) {
			return fmt.Errorf("quest %s has an invalid giver", id)
		}
		for _, req := range quest.Requires {
			if _, ok := data.Quests[req]; !ok || req == id {
				return fmt.Errorf("quest %s requires invalid quest %s", id, req)
			}
		}
		switch quest.Kind {
		case "deliver":
			if _, ok := data.Items[quest.Target]; !ok {
				return fmt.Errorf("quest %s missing target item", id)
			}
			if !obtainable(quest.Target) {
				return fmt.Errorf("quest %s target item has no room spawn or NPC drop", id)
			}
		case "defeat":
			if npc, ok := data.NPCs[quest.Target]; !ok || npc.Role != "enemy" {
				return fmt.Errorf("quest %s missing enemy", id)
			}
		default:
			return fmt.Errorf("quest %s invalid kind %s", id, quest.Kind)
		}
	}
	// Prerequisites must not form a cycle, or the storyline could not be finished.
	state := map[string]int{} // 0 = new, 1 = visiting, 2 = done
	var visit func(id string) error
	visit = func(id string) error {
		switch state[id] {
		case 1:
			return fmt.Errorf("quest prerequisites form a cycle at %s", id)
		case 2:
			return nil
		}
		state[id] = 1
		for _, req := range data.Quests[id].Requires {
			if err := visit(req); err != nil {
				return err
			}
		}
		state[id] = 2
		return nil
	}
	for _, id := range SortedKeys(data.Quests) {
		if err := visit(id); err != nil {
			return err
		}
	}
	// Story text is sent on single protocol lines.
	for _, text := range []string{data.Story.Title, data.Story.Intro, data.Story.Victory} {
		if strings.IndexFunc(text, unicode.IsControl) >= 0 {
			return fmt.Errorf("story text must be a single line without control characters")
		}
	}
	return nil
}

func contains(list []string, value string) bool {
	for _, item := range list {
		if item == value {
			return true
		}
	}
	return false
}
func SortedKeys[Value any](values map[string]Value) []string {
	out := make([]string, 0, len(values))
	for key := range values {
		out = append(out, key)
	}
	sort.Strings(out)
	return out
}
