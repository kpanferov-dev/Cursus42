// Package worldmap tracks where the player is and lays the known rooms out on
// a grid, for the CLI (ASCII) and the GUI (JSON rendered as SVG).
//
// It is purely client-side and only reads standard TAP replies:
//
//	OK connected                 -> player is in the world start room (if known)
//	OK room=<id>                 -> MOVE / FLEE succeeded
//	OK {"room":{...},...}        -> LOOK: room name and exits (map discovery)
//	EVT PLAYER RESPAWN room=<id> -> respawn extension event
//
// Rooms come from the optional local world catalog and/or are discovered
// through LOOK, so the map also works against other teams' servers.
package worldmap

import (
	"encoding/json"
	"fmt"
	"sort"
	"strings"
	"sync"
	"unicode/utf8"

	"tap/internal/world"
)

// Directions in display order, with their grid offsets (y grows southwards).
var directions = []string{"north", "east", "south", "west"}
var offsets = map[string][2]int{"north": {0, -1}, "east": {1, 0}, "south": {0, 1}, "west": {-1, 0}}

type room struct {
	name     string
	exits    map[string]string
	explored bool
	hint     *[2]int
}

// Map is safe for concurrent use.
type Map struct {
	mu      sync.Mutex
	start   string
	rooms   map[string]*room
	current string
	origin  string // first room the player was seen in (layout anchor without a catalog)
	visited map[string]bool
}

// New creates a map, pre-filled from the catalog when one is available.
func New(catalog *world.Data) *Map {
	worldMap := &Map{rooms: map[string]*room{}, visited: map[string]bool{}}
	if catalog == nil {
		return worldMap
	}
	worldMap.start = catalog.Start
	for id, catalogRoom := range catalog.Rooms {
		rr := &room{name: catalogRoom.Name, exits: copyExits(catalogRoom.Exits), explored: true}
		if len(catalogRoom.Map) == 2 {
			rr.hint = &[2]int{catalogRoom.Map[0], catalogRoom.Map[1]}
		}
		worldMap.rooms[id] = rr
	}
	for _, catalogRoom := range catalog.Rooms {
		for _, dest := range catalogRoom.Exits {
			worldMap.ensure(dest)
		}
	}
	return worldMap
}

func copyExits(in map[string]string) map[string]string {
	out := make(map[string]string, len(in))
	for direction, destination := range in {
		out[strings.ToLower(direction)] = destination
	}
	return out
}

func humanize(id string) string {
	if _, rest, ok := strings.Cut(id, "."); ok {
		id = rest
	}
	return strings.ReplaceAll(id, "_", " ")
}

// ensure returns the room, creating an unexplored placeholder if needed.
func (worldMap *Map) ensure(id string) (*room, bool) {
	if info, ok := worldMap.rooms[id]; ok {
		return info, false
	}
	info := &room{name: humanize(id), exits: map[string]string{}}
	worldMap.rooms[id] = info
	return info, true
}

// Observe updates the map from one server line. changed reports any visible
// change; moved reports that the player's current room changed.
func (worldMap *Map) Observe(line string) (changed, moved bool) {
	line = strings.TrimSpace(line)
	worldMap.mu.Lock()
	defer worldMap.mu.Unlock()
	switch {
	case line == "OK connected":
		if worldMap.start != "" {
			return worldMap.moveTo(worldMap.start)
		}
	case strings.HasPrefix(line, "OK room="):
		return worldMap.moveTo(strings.TrimPrefix(line, "OK room="))
	case strings.HasPrefix(line, "EVT PLAYER RESPAWN "):
		for _, field := range strings.Fields(line) {
			if id, ok := strings.CutPrefix(field, "room="); ok {
				return worldMap.moveTo(id)
			}
		}
	case strings.HasPrefix(line, "OK {"):
		var look struct {
			Room *struct {
				ID    string            `json:"id"`
				Name  string            `json:"name"`
				Exits map[string]string `json:"exits"`
			} `json:"room"`
		}
		if json.Unmarshal([]byte(strings.TrimPrefix(line, "OK ")), &look) != nil || look.Room == nil || look.Room.ID == "" {
			return false, false
		}
		learned := worldMap.learn(look.Room.ID, look.Room.Name, look.Room.Exits)
		positionChanged, mv := worldMap.moveTo(look.Room.ID)
		return learned || positionChanged, mv
	}
	return false, false
}

func (worldMap *Map) learn(id, name string, exits map[string]string) bool {
	info, changed := worldMap.ensure(id)
	if name != "" && info.name != name {
		info.name, changed = name, true
	}
	if !info.explored {
		info.explored, changed = true, true
	}
	exits = copyExits(exits)
	if len(exits) != len(info.exits) {
		changed = true
	}
	for dir, dest := range exits {
		if info.exits[dir] != dest {
			changed = true
		}
		if _, added := worldMap.ensure(dest); added {
			changed = true
		}
	}
	info.exits = exits
	return changed
}

func (worldMap *Map) moveTo(id string) (changed, moved bool) {
	if id == "" {
		return false, false
	}
	_, added := worldMap.ensure(id)
	moved = worldMap.current != id
	worldMap.current = id
	if worldMap.origin == "" {
		worldMap.origin = id
	}
	if !worldMap.visited[id] {
		worldMap.visited[id] = true
		changed = true
	}
	return changed || added || moved, moved
}

// CurrentExplored reports whether the exits of the current room are known.
// Clients send an automatic LOOK when they are not.
func (worldMap *Map) CurrentExplored() bool {
	worldMap.mu.Lock()
	defer worldMap.mu.Unlock()
	info := worldMap.rooms[worldMap.current]
	return worldMap.current == "" || (info != nil && info.explored)
}

// ---------------------------------------------------------------- layout

// Cell is one room drawn on the grid (0-based coordinates).
type Cell struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Column   int    `json:"x"`
	Row      int    `json:"y"`
	Current  bool   `json:"current"`
	Visited  bool   `json:"visited"`
	Explored bool   `json:"explored"`
}

// Link is a passage between two rooms. FirstExit is the exit to take from First
// to reach Second (empty for one-way passages), and SecondExit the reverse. Kind is
// "adjacent", "diagonal" or "long" depending on the grid positions.
type Link struct {
	First      string `json:"a"`
	Second     string `json:"b"`
	FirstExit  string `json:"dir_a"`
	SecondExit string `json:"dir_b"`
	Kind       string `json:"kind"`
}

// Snapshot is the complete map state at one moment.
type Snapshot struct {
	Current     string            `json:"current"`
	CurrentName string            `json:"current_name"`
	Width       int               `json:"width"`
	Height      int               `json:"height"`
	Rooms       []Cell            `json:"rooms"`
	Links       []Link            `json:"links"`
	Exits       map[string]string `json:"exits"`
}

func (worldMap *Map) sortedIDs() []string {
	ids := make([]string, 0, len(worldMap.rooms))
	for id := range worldMap.rooms {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	return ids
}

// nearestFree returns target if free, otherwise the closest free grid cell.
func nearestFree(used map[[2]int]string, target [2]int) [2]int {
	if _, taken := used[target]; !taken {
		return target
	}
	for distance := 1; ; distance++ {
		ring := [][2]int{}
		for dy := -distance; dy <= distance; dy++ {
			for dx := -distance; dx <= distance; dx++ {
				if max(abs(dx), abs(dy)) == distance {
					ring = append(ring, [2]int{dx, dy})
				}
			}
		}
		sort.Slice(ring, func(left, right int) bool {
			first, second := ring[left], ring[right]
			if da, db := abs(first[0])+abs(first[1]), abs(second[0])+abs(second[1]); da != db {
				return da < db
			}
			if first[1] != second[1] {
				return first[1] < second[1]
			}
			return first[0] < second[0]
		})
		for _, offset := range ring {
			candidate := [2]int{target[0] + offset[0], target[1] + offset[1]}
			if _, taken := used[candidate]; !taken {
				return candidate
			}
		}
	}
}

func abs(value int) int {
	if value < 0 {
		return -value
	}
	return value
}

// layout places every known room: catalog hints first, then a breadth-first
// walk that puts each neighbour in the direction of its exit when possible.
func (worldMap *Map) layout() map[string][2]int {
	ids := worldMap.sortedIDs()
	pos := map[string][2]int{}
	used := map[[2]int]string{}
	place := func(id string, target [2]int) {
		target = nearestFree(used, target)
		pos[id] = target
		used[target] = id
	}
	for _, id := range ids {
		if hint := worldMap.rooms[id].hint; hint != nil {
			if _, taken := used[*hint]; !taken {
				place(id, *hint)
			}
		}
	}
	root := worldMap.start
	if worldMap.rooms[root] == nil {
		root = worldMap.origin
	}
	// Passages are also followed backwards: a room whose only known link is
	// another room's exit is placed opposite that exit.
	type incoming struct{ from, dir string }
	into := map[string][]incoming{}
	for _, id := range ids {
		for _, dir := range directions {
			if dest := worldMap.rooms[id].exits[dir]; dest != "" {
				into[dest] = append(into[dest], incoming{id, dir})
			}
		}
	}
	queue := []string{}
	if root != "" {
		if _, ok := pos[root]; !ok {
			place(root, [2]int{0, 0})
		}
		queue = append(queue, root)
	}
	for _, id := range ids {
		if _, ok := pos[id]; ok && id != root {
			queue = append(queue, id)
		}
	}
	for len(pos) < len(ids) || len(queue) > 0 {
		if len(queue) == 0 {
			// A disconnected part of the map: start it to the right.
			maxX := 0
			for taken := range used {
				maxX = max(maxX, taken[0])
			}
			for _, id := range ids {
				if _, ok := pos[id]; !ok {
					place(id, [2]int{maxX + 2, 0})
					queue = append(queue, id)
					break
				}
			}
			continue
		}
		id := queue[0]
		queue = queue[1:]
		for _, dir := range directions {
			dest := worldMap.rooms[id].exits[dir]
			if dest == "" || worldMap.rooms[dest] == nil {
				continue
			}
			if _, ok := pos[dest]; ok {
				continue
			}
			from := pos[id]
			place(dest, [2]int{from[0] + offsets[dir][0], from[1] + offsets[dir][1]})
			queue = append(queue, dest)
		}
		for _, in := range into[id] {
			if _, ok := pos[in.from]; ok {
				continue
			}
			from := pos[id]
			place(in.from, [2]int{from[0] - offsets[in.dir][0], from[1] - offsets[in.dir][1]})
			queue = append(queue, in.from)
		}
	}
	return pos
}

// Snapshot computes the current layout.
func (worldMap *Map) Snapshot() Snapshot {
	worldMap.mu.Lock()
	defer worldMap.mu.Unlock()
	snapshot := Snapshot{Current: worldMap.current, Rooms: []Cell{}, Links: []Link{}, Exits: map[string]string{}}
	if len(worldMap.rooms) == 0 {
		return snapshot
	}
	pos := worldMap.layout()
	minX, minY, maxX, maxY := 1<<30, 1<<30, -(1 << 30), -(1 << 30)
	for _, spot := range pos {
		minX, minY = min(minX, spot[0]), min(minY, spot[1])
		maxX, maxY = max(maxX, spot[0]), max(maxY, spot[1])
	}
	snapshot.Width, snapshot.Height = maxX-minX+1, maxY-minY+1
	ids := worldMap.sortedIDs()
	for _, id := range ids {
		info, spot := worldMap.rooms[id], pos[id]
		snapshot.Rooms = append(snapshot.Rooms, Cell{ID: id, Name: info.name, Column: spot[0] - minX, Row: spot[1] - minY, Current: id == worldMap.current, Visited: worldMap.visited[id], Explored: info.explored})
	}
	if info := worldMap.rooms[worldMap.current]; info != nil {
		snapshot.CurrentName = info.name
		for dir, dest := range info.exits {
			snapshot.Exits[dir] = dest
		}
	}
	links := map[[2]string]*Link{}
	for _, id := range ids {
		for _, dir := range directions {
			dest := worldMap.rooms[id].exits[dir]
			if dest == "" || dest == id {
				continue
			}
			key := [2]string{id, dest}
			if dest < id {
				key = [2]string{dest, id}
			}
			link := links[key]
			if link == nil {
				link = &Link{First: key[0], Second: key[1]}
				links[key] = link
			}
			if id == link.First && link.FirstExit == "" {
				link.FirstExit = dir
			} else if id == link.Second && link.SecondExit == "" {
				link.SecondExit = dir
			}
		}
	}
	for _, link := range links {
		cellA, cellB := pos[link.First], pos[link.Second]
		dx, dy := abs(cellA[0]-cellB[0]), abs(cellA[1]-cellB[1])
		switch {
		case dx+dy == 1:
			link.Kind = "adjacent"
		case dx == 1 && dy == 1:
			link.Kind = "diagonal"
		default:
			link.Kind = "long"
		}
		snapshot.Links = append(snapshot.Links, *link)
	}
	sort.Slice(snapshot.Links, func(left, right int) bool {
		if snapshot.Links[left].First != snapshot.Links[right].First {
			return snapshot.Links[left].First < snapshot.Links[right].First
		}
		return snapshot.Links[left].Second < snapshot.Links[right].Second
	})
	return snapshot
}

// JSON returns the snapshot as a single-line JSON document.
func (worldMap *Map) JSON() string {
	encoded, err := json.Marshal(worldMap.Snapshot())
	if err != nil {
		return "{}"
	}
	return string(encoded)
}

// ---------------------------------------------------------------- ASCII

const (
	ansiReset   = "\x1b[0m"
	ansiCurrent = "\x1b[1;30;46m" // bold, black on cyan
	ansiDim     = "\x1b[2m"
)

// Header is the one-line "you are here" summary.
func (snapshot Snapshot) Header() string {
	if snapshot.Current == "" {
		return "You are here: unknown (type LOOK)"
	}
	dirs := []string{}
	for _, direction := range directions {
		if _, ok := snapshot.Exits[direction]; ok {
			dirs = append(dirs, direction)
		}
	}
	exits := "none known"
	if len(dirs) > 0 {
		exits = strings.Join(dirs, ", ")
	}
	return fmt.Sprintf("You are here: %s   (exits: %s)", snapshot.CurrentName, exits)
}

func fit(text string, width int) string {
	length := utf8.RuneCountInString(text)
	if length > width {
		runes := []rune(text)
		return string(runes[:width-1]) + "~"
	}
	return text + strings.Repeat(" ", width-length)
}

// ASCII draws the map. maxWidth (0 = unlimited) shrinks room labels to fit
// the terminal; color adds ANSI highlighting for the current room.
func (snapshot Snapshot) ASCII(maxWidth int, color bool) []string {
	if len(snapshot.Rooms) == 0 {
		return []string{"(map unknown: type LOOK to discover the room)"}
	}
	names := map[string]string{}
	grid := map[[2]int]Cell{}
	inner := 0
	for _, entry := range snapshot.Rooms {
		names[entry.ID] = entry.Name
		grid[[2]int{entry.Column, entry.Row}] = entry
		inner = max(inner, utf8.RuneCountInString(entry.Name)+1)
	}
	if maxWidth > 0 && snapshot.Width > 0 {
		budget := (maxWidth-3*(snapshot.Width-1))/snapshot.Width - 2
		inner = min(inner, budget)
	}
	inner = max(inner, 6)
	cellW := inner + 2
	pos := map[string][2]int{}
	for _, entry := range snapshot.Rooms {
		pos[entry.ID] = [2]int{entry.Column, entry.Row}
	}
	horiz, vert, back, fwd := map[[2]int]bool{}, map[[2]int]bool{}, map[[2]int]bool{}, map[[2]int]bool{}
	long := []string{}
	for _, link := range snapshot.Links {
		upper, lower := pos[link.First], pos[link.Second]
		if upper[1] > lower[1] || (upper[1] == lower[1] && upper[0] > lower[0]) {
			upper, lower = lower, upper
		}
		switch link.Kind {
		case "adjacent":
			if upper[1] == lower[1] {
				horiz[upper] = true
			} else {
				vert[upper] = true
			}
		case "diagonal":
			if lower[0] > upper[0] {
				back[upper] = true // upper room is up-left of the lower one: '\'
			} else {
				fwd[[2]int{lower[0], upper[1]}] = true // upper room is up-right: '/'
			}
		default:
			long = append(long, fmt.Sprintf("  %s (%s) <-> %s (%s)", names[link.First], dirOrDash(link.FirstExit), names[link.Second], dirOrDash(link.SecondExit)))
		}
	}
	lines := []string{}
	unexplored := false
	for gridRow := 0; gridRow < snapshot.Height; gridRow++ {
		var row strings.Builder
		for gridColumn := 0; gridColumn < snapshot.Width; gridColumn++ {
			if gridColumn > 0 {
				if horiz[[2]int{gridColumn - 1, gridRow}] {
					row.WriteString("---")
				} else {
					row.WriteString("   ")
				}
			}
			entry, ok := grid[[2]int{gridColumn, gridRow}]
			if !ok {
				row.WriteString(strings.Repeat(" ", cellW))
				continue
			}
			label := entry.Name
			if !entry.Explored {
				label, unexplored = "?"+label, true
			}
			if entry.Current {
				label = "@" + label
			}
			text := "[" + fit(label, inner) + "]"
			switch {
			case color && entry.Current:
				text = ansiCurrent + text + ansiReset
			case color && !entry.Explored:
				text = ansiDim + text + ansiReset
			}
			row.WriteString(text)
		}
		lines = append(lines, strings.TrimRight(row.String(), " "))
		if gridRow == snapshot.Height-1 {
			break
		}
		gap := []rune(strings.Repeat(" ", snapshot.Width*cellW+(snapshot.Width-1)*3))
		for gridColumn := 0; gridColumn < snapshot.Width; gridColumn++ {
			if vert[[2]int{gridColumn, gridRow}] {
				gap[gridColumn*(cellW+3)+cellW/2] = '|'
			}
			if gridColumn < snapshot.Width-1 {
				col := gridColumn*(cellW+3) + cellW + 1
				switch {
				case back[[2]int{gridColumn, gridRow}] && fwd[[2]int{gridColumn, gridRow}]:
					gap[col] = 'X'
				case back[[2]int{gridColumn, gridRow}]:
					gap[col] = '\\'
				case fwd[[2]int{gridColumn, gridRow}]:
					gap[col] = '/'
				}
			}
		}
		lines = append(lines, strings.TrimRight(string(gap), " "))
	}
	if len(long) > 0 {
		lines = append(lines, "Long paths (exit to take in brackets):")
		lines = append(lines, long...)
	}
	legend := "@ = you are here"
	if unexplored {
		legend += "   ? = not explored yet"
	}
	return append(lines, legend)
}

func dirOrDash(dir string) string {
	if dir == "" {
		return "one-way"
	}
	return dir
}
