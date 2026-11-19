package worldmap

import (
	"path/filepath"
	"strings"
	"testing"

	"tap/internal/narrator"
)

func catalogMap(t *testing.T) *Map {
	t.Helper()
	cat := narrator.LoadCatalog(filepath.Join("..", "..", "world", "world.json"))
	if cat == nil {
		t.Fatal("catalog not loaded")
	}
	return New(cat)
}

func cell(s Snapshot, id string) Cell {
	for _, c := range s.Rooms {
		if c.ID == id {
			return c
		}
	}
	return Cell{}
}

func TestTracksPositionFromReplies(t *testing.T) {
	m := catalogMap(t)
	if _, moved := m.Observe("OK connected"); !moved {
		t.Fatal("connect should place the player in the start room")
	}
	if s := m.Snapshot(); s.Current != "loc.square" || s.CurrentName != "Clockwork Square" {
		t.Fatalf("start: %+v", s)
	}
	m.Observe("OK room=loc.market")
	m.Observe("EVT ROOM PRESENCE ENTER alice") // ignored
	if changed, _ := m.Observe(`OK {"gold":0,"hp":100,"max_hp":100,"status":"healthy"}`); changed {
		t.Fatal("STATUS JSON must not change the map")
	}
	s := m.Snapshot()
	if s.Current != "loc.market" || !cell(s, "loc.market").Current || !cell(s, "loc.square").Visited || cell(s, "loc.forge").Visited {
		t.Fatalf("after move: %+v", s)
	}
	m.Observe("EVT PLAYER RESPAWN room=loc.square hp=35")
	if m.Snapshot().Current != "loc.square" {
		t.Fatal("respawn not tracked")
	}
}

func TestCatalogLayoutUsesHints(t *testing.T) {
	m := catalogMap(t)
	m.Observe("OK connected")
	s := m.Snapshot()
	if s.Width != 4 || s.Height != 5 || len(s.Rooms) != 12 {
		t.Fatalf("grid %dx%d with %d rooms", s.Width, s.Height, len(s.Rooms))
	}
	sq, market := cell(s, "loc.square"), cell(s, "loc.market")
	if market.X != sq.X || market.Y != sq.Y-1 {
		t.Fatalf("market should be north of square: %+v %+v", sq, market)
	}
	long := 0
	for _, l := range s.Links {
		if l.Kind == "long" {
			long++
		}
	}
	// A 5-room loop can't be drawn on a square grid: exactly one long path.
	if long != 1 {
		t.Fatalf("expected 1 long path, got %d: %+v", long, s.Links)
	}
	text := strings.Join(s.ASCII(0, false), "\n")
	for _, want := range []string{"[@Clockwork Square", "Old Harbor (south) <-> Murkfen Marsh (west)", "---", "|", "\\"} {
		if !strings.Contains(text, want) {
			t.Fatalf("ASCII map lacks %q:\n%s", want, text)
		}
	}
	for _, line := range s.ASCII(80, true) {
		plain := strings.NewReplacer(ansiCurrent, "", ansiDim, "", ansiReset, "").Replace(line)
		if len([]rune(plain)) > 80 {
			t.Fatalf("line wider than 80 columns: %q", plain)
		}
	}
}

func TestDiscoversUnknownWorld(t *testing.T) {
	m := New(nil) // another team's server: no catalog
	if lines := m.Snapshot().ASCII(0, false); !strings.Contains(lines[0], "LOOK") {
		t.Fatalf("empty map should suggest LOOK: %v", lines)
	}
	m.Observe(`OK {"room":{"id":"r.hall","name":"Great Hall","exits":{"north":"r.tower","east":"r.kitchen"}},"players":[],"items":[],"npcs":[]}`)
	if m.CurrentExplored() != true {
		t.Fatal("hall was looked at")
	}
	m.Observe("OK room=r.tower")
	if m.CurrentExplored() {
		t.Fatal("tower has not been looked at yet")
	}
	s := m.Snapshot()
	hall, tower, kitchen := cell(s, "r.hall"), cell(s, "r.tower"), cell(s, "r.kitchen")
	if tower.Y != hall.Y-1 || kitchen.X != hall.X+1 || tower.Explored || !tower.Current || tower.Name != "tower" {
		t.Fatalf("discovered layout: %+v", s.Rooms)
	}
	text := strings.Join(s.ASCII(0, false), "\n")
	if !strings.Contains(text, "[@?tower") || !strings.Contains(text, "? = not explored yet") {
		t.Fatal(text)
	}
}
