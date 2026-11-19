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
func (n NPC) QuestList() []string {
	out := []string{}
	if n.Quest != "" {
		out = append(out, n.Quest)
	}
	for _, q := range n.Quests {
		if q != n.Quest {
			out = append(out, q)
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
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var d Data
	if err := json.Unmarshal(b, &d); err != nil {
		return nil, fmt.Errorf("parse world: %w", err)
	}
	if err := d.Validate(); err != nil {
		return nil, err
	}
	return &d, nil
}
func (d *Data) Validate() error {
	if _, ok := d.Rooms[d.Start]; !ok {
		return fmt.Errorf("start room %q does not exist", d.Start)
	}
	if len(d.Rooms) < 8 {
		return fmt.Errorf("at least 8 rooms required, got %d", len(d.Rooms))
	}
	usedCells := make(map[[2]int]string)
	for id, r := range d.Rooms {
		if r.Map == nil {
			continue
		}
		if len(r.Map) != 2 {
			return fmt.Errorf("room %s map position must be [x, y]", id)
		}
		cell := [2]int{r.Map[0], r.Map[1]}
		if prev, ok := usedCells[cell]; ok {
			return fmt.Errorf("rooms %s and %s share map position %v", prev, id, r.Map)
		}
		usedCells[cell] = id
	}
	usedItems := make(map[string]string)
	usedNPCs := make(map[string]string)
	for id, r := range d.Rooms {
		if id == "" || r.Name == "" || r.Description == "" {
			return fmt.Errorf("incomplete room %q", id)
		}
		for dir, dest := range r.Exits {
			if _, ok := d.Rooms[dest]; !ok {
				return fmt.Errorf("room %s exit %s references missing %s", id, dir, dest)
			}
			if dir != "north" && dir != "south" && dir != "east" && dir != "west" {
				return fmt.Errorf("invalid direction %s in %s", dir, id)
			}
		}
		for _, itemID := range r.Items {
			if _, ok := d.Items[itemID]; !ok {
				return fmt.Errorf("room %s references unknown item %s", id, itemID)
			}
			if prev, ok := usedItems[itemID]; ok {
				return fmt.Errorf("item %s duplicated in %s and %s", itemID, prev, id)
			}
			usedItems[itemID] = id
		}
		for _, npcID := range r.NPCs {
			if _, ok := d.NPCs[npcID]; !ok {
				return fmt.Errorf("room %s references unknown NPC %s", id, npcID)
			}
			if prev, ok := usedNPCs[npcID]; ok {
				return fmt.Errorf("NPC %s duplicated in %s and %s", npcID, prev, id)
			}
			usedNPCs[npcID] = id
		}
	}
	// All rooms must be reachable from start, irrespective of optional branches.
	visited := map[string]bool{d.Start: true}
	queue := []string{d.Start}
	for len(queue) > 0 {
		room := queue[0]
		queue = queue[1:]
		for _, dest := range d.Rooms[room].Exits {
			if !visited[dest] {
				visited[dest] = true
				queue = append(queue, dest)
			}
		}
	}
	if len(visited) != len(d.Rooms) {
		return fmt.Errorf("world is disconnected: %d of %d rooms reachable", len(visited), len(d.Rooms))
	}
	if len(d.Items) < 4 || len(d.NPCs) < 3 || len(d.Quests) < 2 {
		return fmt.Errorf("world needs 4 items, 3 NPCs, and 2 quests")
	}
	for id, n := range d.NPCs {
		if n.HP < 1 || n.Name == "" {
			return fmt.Errorf("invalid NPC %s", id)
		}
		if _, ok := usedNPCs[id]; !ok {
			return fmt.Errorf("NPC %s has no spawn room", id)
		}
		for _, q := range n.QuestList() {
			if _, ok := d.Quests[q]; !ok {
				return fmt.Errorf("NPC %s points to nonexistent quest %s", id, q)
			}
		}
		if n.Loot != "" {
			if _, ok := d.Items[n.Loot]; !ok {
				return fmt.Errorf("NPC %s drops unknown item %s", id, n.Loot)
			}
		}
		if n.RequiresQuest != "" {
			if _, ok := d.Quests[n.RequiresQuest]; !ok {
				return fmt.Errorf("NPC %s requires unknown quest %s", id, n.RequiresQuest)
			}
		}
	}
	// An item exists in the world if it spawns in a room or is dropped by an NPC.
	obtainable := func(item string) bool {
		if _, ok := usedItems[item]; ok {
			return true
		}
		for _, n := range d.NPCs {
			if n.Loot == item {
				return true
			}
		}
		return false
	}
	for id, it := range d.Items {
		if it.Heal < 0 || it.Attack < 0 || it.Defense < 0 {
			return fmt.Errorf("item %s has negative stats", id)
		}
	}
	for id, r := range d.Rooms {
		for dir, item := range r.Locks {
			if _, ok := r.Exits[dir]; !ok {
				return fmt.Errorf("room %s locks missing exit %s", id, dir)
			}
			if _, ok := d.Items[item]; !ok || !obtainable(item) {
				return fmt.Errorf("room %s lock needs unobtainable item %s", id, item)
			}
		}
	}
	for id, q := range d.Quests {
		giver, ok := d.NPCs[q.Giver]
		if !ok || !contains(giver.QuestList(), id) {
			return fmt.Errorf("quest %s has an invalid giver", id)
		}
		for _, req := range q.Requires {
			if _, ok := d.Quests[req]; !ok || req == id {
				return fmt.Errorf("quest %s requires invalid quest %s", id, req)
			}
		}
		switch q.Kind {
		case "deliver":
			if _, ok := d.Items[q.Target]; !ok {
				return fmt.Errorf("quest %s missing target item", id)
			}
			if !obtainable(q.Target) {
				return fmt.Errorf("quest %s target item has no room spawn or NPC drop", id)
			}
		case "defeat":
			if n, ok := d.NPCs[q.Target]; !ok || n.Role != "enemy" {
				return fmt.Errorf("quest %s missing enemy", id)
			}
		default:
			return fmt.Errorf("quest %s invalid kind %s", id, q.Kind)
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
		for _, req := range d.Quests[id].Requires {
			if err := visit(req); err != nil {
				return err
			}
		}
		state[id] = 2
		return nil
	}
	for _, id := range SortedKeys(d.Quests) {
		if err := visit(id); err != nil {
			return err
		}
	}
	// Story text is sent on single protocol lines.
	for _, text := range []string{d.Story.Title, d.Story.Intro, d.Story.Victory} {
		if strings.IndexFunc(text, unicode.IsControl) >= 0 {
			return fmt.Errorf("story text must be a single line without control characters")
		}
	}
	return nil
}

func contains(list []string, value string) bool {
	for _, v := range list {
		if v == value {
			return true
		}
	}
	return false
}
func SortedKeys[V any](m map[string]V) []string {
	out := make([]string, 0, len(m))
	for key := range m {
		out = append(out, key)
	}
	sort.Strings(out)
	return out
}
