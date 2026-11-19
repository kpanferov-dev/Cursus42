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
	m := &Map{rooms: map[string]*room{}, visited: map[string]bool{}}
	if catalog == nil {
		return m
	}
	m.start = catalog.Start
	for id, r := range catalog.Rooms {
		rr := &room{name: r.Name, exits: copyExits(r.Exits), explored: true}
		if len(r.Map) == 2 {
			rr.hint = &[2]int{r.Map[0], r.Map[1]}
		}
		m.rooms[id] = rr
	}
	for _, r := range catalog.Rooms {
		for _, dest := range r.Exits {
			m.ensure(dest)
		}
	}
	return m
}

func copyExits(in map[string]string) map[string]string {
	out := make(map[string]string, len(in))
	for k, v := range in {
		out[strings.ToLower(k)] = v
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
func (m *Map) ensure(id string) (*room, bool) {
	if r, ok := m.rooms[id]; ok {
		return r, false
	}
	r := &room{name: humanize(id), exits: map[string]string{}}
	m.rooms[id] = r
	return r, true
}

// Observe updates the map from one server line. changed reports any visible
// change; moved reports that the player's current room changed.
func (m *Map) Observe(line string) (changed, moved bool) {
	line = strings.TrimSpace(line)
	m.mu.Lock()
	defer m.mu.Unlock()
	switch {
	case line == "OK connected":
		if m.start != "" {
			return m.moveTo(m.start)
		}
	case strings.HasPrefix(line, "OK room="):
		return m.moveTo(strings.TrimPrefix(line, "OK room="))
	case strings.HasPrefix(line, "EVT PLAYER RESPAWN "):
		for _, f := range strings.Fields(line) {
			if id, ok := strings.CutPrefix(f, "room="); ok {
				return m.moveTo(id)
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
		learned := m.learn(look.Room.ID, look.Room.Name, look.Room.Exits)
		c, mv := m.moveTo(look.Room.ID)
		return learned || c, mv
	}
	return false, false
}

func (m *Map) learn(id, name string, exits map[string]string) bool {
	r, changed := m.ensure(id)
	if name != "" && r.name != name {
		r.name, changed = name, true
	}
	if !r.explored {
		r.explored, changed = true, true
	}
	exits = copyExits(exits)
	if len(exits) != len(r.exits) {
		changed = true
	}
	for dir, dest := range exits {
		if r.exits[dir] != dest {
			changed = true
		}
		if _, added := m.ensure(dest); added {
			changed = true
		}
	}
	r.exits = exits
	return changed
}

func (m *Map) moveTo(id string) (changed, moved bool) {
	if id == "" {
		return false, false
	}
	_, added := m.ensure(id)
	moved = m.current != id
	m.current = id
	if m.origin == "" {
		m.origin = id
	}
	if !m.visited[id] {
		m.visited[id] = true
		changed = true
	}
	return changed || added || moved, moved
}

// CurrentExplored reports whether the exits of the current room are known.
// Clients send an automatic LOOK when they are not.
func (m *Map) CurrentExplored() bool {
	m.mu.Lock()
	defer m.mu.Unlock()
	r := m.rooms[m.current]
	return m.current == "" || (r != nil && r.explored)
}

// ---------------------------------------------------------------- layout

// Cell is one room drawn on the grid (0-based coordinates).
type Cell struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	X        int    `json:"x"`
	Y        int    `json:"y"`
	Current  bool   `json:"current"`
	Visited  bool   `json:"visited"`
	Explored bool   `json:"explored"`
}

// Link is a passage between two rooms. DirA is the exit to take from A to
// reach B (empty for one-way passages), and DirB the reverse. Kind is
// "adjacent", "diagonal" or "long" depending on the grid positions.
type Link struct {
	A    string `json:"a"`
	B    string `json:"b"`
	DirA string `json:"dir_a"`
	DirB string `json:"dir_b"`
	Kind string `json:"kind"`
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

func (m *Map) sortedIDs() []string {
	ids := make([]string, 0, len(m.rooms))
	for id := range m.rooms {
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
	for d := 1; ; d++ {
		ring := [][2]int{}
		for dy := -d; dy <= d; dy++ {
			for dx := -d; dx <= d; dx++ {
				if max(abs(dx), abs(dy)) == d {
					ring = append(ring, [2]int{dx, dy})
				}
			}
		}
		sort.Slice(ring, func(i, j int) bool {
			a, b := ring[i], ring[j]
			if da, db := abs(a[0])+abs(a[1]), abs(b[0])+abs(b[1]); da != db {
				return da < db
			}
			if a[1] != b[1] {
				return a[1] < b[1]
			}
			return a[0] < b[0]
		})
		for _, o := range ring {
			p := [2]int{target[0] + o[0], target[1] + o[1]}
			if _, taken := used[p]; !taken {
				return p
			}
		}
	}
}

func abs(v int) int {
	if v < 0 {
		return -v
	}
	return v
}

// layout places every known room: catalog hints first, then a breadth-first
// walk that puts each neighbour in the direction of its exit when possible.
func (m *Map) layout() map[string][2]int {
	ids := m.sortedIDs()
	pos := map[string][2]int{}
	used := map[[2]int]string{}
	place := func(id string, p [2]int) {
		p = nearestFree(used, p)
		pos[id] = p
		used[p] = id
	}
	for _, id := range ids {
		if h := m.rooms[id].hint; h != nil {
			if _, taken := used[*h]; !taken {
				place(id, *h)
			}
		}
	}
	root := m.start
	if m.rooms[root] == nil {
		root = m.origin
	}
	// Passages are also followed backwards: a room whose only known link is
	// another room's exit is placed opposite that exit.
	type incoming struct{ from, dir string }
	into := map[string][]incoming{}
	for _, id := range ids {
		for _, dir := range directions {
			if dest := m.rooms[id].exits[dir]; dest != "" {
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
			for p := range used {
				maxX = max(maxX, p[0])
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
			dest := m.rooms[id].exits[dir]
			if dest == "" || m.rooms[dest] == nil {
				continue
			}
			if _, ok := pos[dest]; ok {
				continue
			}
			p := pos[id]
			place(dest, [2]int{p[0] + offsets[dir][0], p[1] + offsets[dir][1]})
			queue = append(queue, dest)
		}
		for _, in := range into[id] {
			if _, ok := pos[in.from]; ok {
				continue
			}
			p := pos[id]
			place(in.from, [2]int{p[0] - offsets[in.dir][0], p[1] - offsets[in.dir][1]})
			queue = append(queue, in.from)
		}
	}
	return pos
}

// Snapshot computes the current layout.
func (m *Map) Snapshot() Snapshot {
	m.mu.Lock()
	defer m.mu.Unlock()
	s := Snapshot{Current: m.current, Rooms: []Cell{}, Links: []Link{}, Exits: map[string]string{}}
	if len(m.rooms) == 0 {
		return s
	}
	pos := m.layout()
	minX, minY, maxX, maxY := 1<<30, 1<<30, -(1 << 30), -(1 << 30)
	for _, p := range pos {
		minX, minY = min(minX, p[0]), min(minY, p[1])
		maxX, maxY = max(maxX, p[0]), max(maxY, p[1])
	}
	s.Width, s.Height = maxX-minX+1, maxY-minY+1
	ids := m.sortedIDs()
	for _, id := range ids {
		r, p := m.rooms[id], pos[id]
		s.Rooms = append(s.Rooms, Cell{ID: id, Name: r.name, X: p[0] - minX, Y: p[1] - minY, Current: id == m.current, Visited: m.visited[id], Explored: r.explored})
	}
	if r := m.rooms[m.current]; r != nil {
		s.CurrentName = r.name
		for dir, dest := range r.exits {
			s.Exits[dir] = dest
		}
	}
	links := map[[2]string]*Link{}
	for _, id := range ids {
		for _, dir := range directions {
			dest := m.rooms[id].exits[dir]
			if dest == "" || dest == id {
				continue
			}
			key := [2]string{id, dest}
			if dest < id {
				key = [2]string{dest, id}
			}
			l := links[key]
			if l == nil {
				l = &Link{A: key[0], B: key[1]}
				links[key] = l
			}
			if id == l.A && l.DirA == "" {
				l.DirA = dir
			} else if id == l.B && l.DirB == "" {
				l.DirB = dir
			}
		}
	}
	for _, l := range links {
		a, b := pos[l.A], pos[l.B]
		dx, dy := abs(a[0]-b[0]), abs(a[1]-b[1])
		switch {
		case dx+dy == 1:
			l.Kind = "adjacent"
		case dx == 1 && dy == 1:
			l.Kind = "diagonal"
		default:
			l.Kind = "long"
		}
		s.Links = append(s.Links, *l)
	}
	sort.Slice(s.Links, func(i, j int) bool {
		if s.Links[i].A != s.Links[j].A {
			return s.Links[i].A < s.Links[j].A
		}
		return s.Links[i].B < s.Links[j].B
	})
	return s
}

// JSON returns the snapshot as a single-line JSON document.
func (m *Map) JSON() string {
	b, err := json.Marshal(m.Snapshot())
	if err != nil {
		return "{}"
	}
	return string(b)
}

// ---------------------------------------------------------------- ASCII

const (
	ansiReset   = "\x1b[0m"
	ansiCurrent = "\x1b[1;30;46m" // bold, black on cyan
	ansiDim     = "\x1b[2m"
)

// Header is the one-line "you are here" summary.
func (s Snapshot) Header() string {
	if s.Current == "" {
		return "You are here: unknown (type LOOK)"
	}
	dirs := []string{}
	for _, d := range directions {
		if _, ok := s.Exits[d]; ok {
			dirs = append(dirs, d)
		}
	}
	exits := "none known"
	if len(dirs) > 0 {
		exits = strings.Join(dirs, ", ")
	}
	return fmt.Sprintf("You are here: %s   (exits: %s)", s.CurrentName, exits)
}

func fit(text string, width int) string {
	n := utf8.RuneCountInString(text)
	if n > width {
		r := []rune(text)
		return string(r[:width-1]) + "~"
	}
	return text + strings.Repeat(" ", width-n)
}

// ASCII draws the map. maxWidth (0 = unlimited) shrinks room labels to fit
// the terminal; color adds ANSI highlighting for the current room.
func (s Snapshot) ASCII(maxWidth int, color bool) []string {
	if len(s.Rooms) == 0 {
		return []string{"(map unknown: type LOOK to discover the room)"}
	}
	names := map[string]string{}
	grid := map[[2]int]Cell{}
	inner := 0
	for _, c := range s.Rooms {
		names[c.ID] = c.Name
		grid[[2]int{c.X, c.Y}] = c
		inner = max(inner, utf8.RuneCountInString(c.Name)+1)
	}
	if maxWidth > 0 && s.Width > 0 {
		budget := (maxWidth-3*(s.Width-1))/s.Width - 2
		inner = min(inner, budget)
	}
	inner = max(inner, 6)
	cellW := inner + 2
	pos := map[string][2]int{}
	for _, c := range s.Rooms {
		pos[c.ID] = [2]int{c.X, c.Y}
	}
	horiz, vert, back, fwd := map[[2]int]bool{}, map[[2]int]bool{}, map[[2]int]bool{}, map[[2]int]bool{}
	long := []string{}
	for _, l := range s.Links {
		a, b := pos[l.A], pos[l.B]
		if a[1] > b[1] || (a[1] == b[1] && a[0] > b[0]) {
			a, b = b, a
		}
		switch l.Kind {
		case "adjacent":
			if a[1] == b[1] {
				horiz[a] = true
			} else {
				vert[a] = true
			}
		case "diagonal":
			if b[0] > a[0] {
				back[a] = true // a is upper-left: '\'
			} else {
				fwd[[2]int{b[0], a[1]}] = true // a is upper-right: '/'
			}
		default:
			long = append(long, fmt.Sprintf("  %s (%s) <-> %s (%s)", names[l.A], dirOrDash(l.DirA), names[l.B], dirOrDash(l.DirB)))
		}
	}
	lines := []string{}
	unexplored := false
	for y := 0; y < s.Height; y++ {
		var row strings.Builder
		for x := 0; x < s.Width; x++ {
			if x > 0 {
				if horiz[[2]int{x - 1, y}] {
					row.WriteString("---")
				} else {
					row.WriteString("   ")
				}
			}
			c, ok := grid[[2]int{x, y}]
			if !ok {
				row.WriteString(strings.Repeat(" ", cellW))
				continue
			}
			label := c.Name
			if !c.Explored {
				label, unexplored = "?"+label, true
			}
			if c.Current {
				label = "@" + label
			}
			text := "[" + fit(label, inner) + "]"
			switch {
			case color && c.Current:
				text = ansiCurrent + text + ansiReset
			case color && !c.Explored:
				text = ansiDim + text + ansiReset
			}
			row.WriteString(text)
		}
		lines = append(lines, strings.TrimRight(row.String(), " "))
		if y == s.Height-1 {
			break
		}
		gap := []rune(strings.Repeat(" ", s.Width*cellW+(s.Width-1)*3))
		for x := 0; x < s.Width; x++ {
			if vert[[2]int{x, y}] {
				gap[x*(cellW+3)+cellW/2] = '|'
			}
			if x < s.Width-1 {
				col := x*(cellW+3) + cellW + 1
				switch {
				case back[[2]int{x, y}] && fwd[[2]int{x, y}]:
					gap[col] = 'X'
				case back[[2]int{x, y}]:
					gap[col] = '\\'
				case fwd[[2]int{x, y}]:
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
