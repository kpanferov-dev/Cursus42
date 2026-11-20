package worldmap

import (
	"path/filepath"
	"strings"
	"testing"

	"tap/internal/narrator"
)

func catalogMap(test *testing.T) *Map {
	test.Helper()
	cat := narrator.LoadCatalog(filepath.Join("..", "..", "world", "world.json"))
	if cat == nil {
		test.Fatal("catalog not loaded")
	}
	return New(cat)
}

func cell(snapshot Snapshot, id string) Cell {
	for _, candidate := range snapshot.Rooms {
		if candidate.ID == id {
			return candidate
		}
	}
	return Cell{}
}

func TestTracksPositionFromReplies(test *testing.T) {
	worldMap := catalogMap(test)
	if _, moved := worldMap.Observe("OK connected"); !moved {
		test.Fatal("connect should place the player in the start room")
	}
	if snapshot := worldMap.Snapshot(); snapshot.Current != "loc.square" || snapshot.CurrentName != "Clockwork Square" {
		test.Fatalf("start: %+v", snapshot)
	}
	worldMap.Observe("OK room=loc.market")
	worldMap.Observe("EVT ROOM PRESENCE ENTER alice") // ignored
	if changed, _ := worldMap.Observe(`OK {"gold":0,"hp":100,"max_hp":100,"status":"healthy"}`); changed {
		test.Fatal("STATUS JSON must not change the map")
	}
	snapshot := worldMap.Snapshot()
	if snapshot.Current != "loc.market" || !cell(snapshot, "loc.market").Current || !cell(snapshot, "loc.square").Visited || cell(snapshot, "loc.forge").Visited {
		test.Fatalf("after move: %+v", snapshot)
	}
	worldMap.Observe("EVT PLAYER RESPAWN room=loc.square hp=35")
	if worldMap.Snapshot().Current != "loc.square" {
		test.Fatal("respawn not tracked")
	}
}

func TestCatalogLayoutUsesHints(test *testing.T) {
	worldMap := catalogMap(test)
	worldMap.Observe("OK connected")
	snapshot := worldMap.Snapshot()
	if snapshot.Width != 4 || snapshot.Height != 5 || len(snapshot.Rooms) != 12 {
		test.Fatalf("grid %dx%d with %d rooms", snapshot.Width, snapshot.Height, len(snapshot.Rooms))
	}
	sq, market := cell(snapshot, "loc.square"), cell(snapshot, "loc.market")
	if market.Column != sq.Column || market.Row != sq.Row-1 {
		test.Fatalf("market should be north of square: %+v %+v", sq, market)
	}
	long := 0
	for _, link := range snapshot.Links {
		if link.Kind == "long" {
			long++
		}
	}
	// A 5-room loop can't be drawn on a square grid: exactly one long path.
	if long != 1 {
		test.Fatalf("expected 1 long path, got %d: %+v", long, snapshot.Links)
	}
	text := strings.Join(snapshot.ASCII(0, false), "\n")
	for _, want := range []string{"[@Clockwork Square", "Old Harbor (south) <-> Murkfen Marsh (west)", "---", "|", "\\"} {
		if !strings.Contains(text, want) {
			test.Fatalf("ASCII map lacks %q:\n%s", want, text)
		}
	}
	for _, line := range snapshot.ASCII(80, true) {
		plain := strings.NewReplacer(ansiCurrent, "", ansiDim, "", ansiReset, "").Replace(line)
		if len([]rune(plain)) > 80 {
			test.Fatalf("line wider than 80 columns: %q", plain)
		}
	}
}

func TestDiscoversUnknownWorld(test *testing.T) {
	worldMap := New(nil) // another team's server: no catalog
	if lines := worldMap.Snapshot().ASCII(0, false); !strings.Contains(lines[0], "LOOK") {
		test.Fatalf("empty map should suggest LOOK: %v", lines)
	}
	worldMap.Observe(`OK {"room":{"id":"r.hall","name":"Great Hall","exits":{"north":"r.tower","east":"r.kitchen"}},"players":[],"items":[],"npcs":[]}`)
	if worldMap.CurrentExplored() != true {
		test.Fatal("hall was looked at")
	}
	worldMap.Observe("OK room=r.tower")
	if worldMap.CurrentExplored() {
		test.Fatal("tower has not been looked at yet")
	}
	snapshot := worldMap.Snapshot()
	hall, tower, kitchen := cell(snapshot, "r.hall"), cell(snapshot, "r.tower"), cell(snapshot, "r.kitchen")
	if tower.Row != hall.Row-1 || kitchen.Column != hall.Column+1 || tower.Explored || !tower.Current || tower.Name != "tower" {
		test.Fatalf("discovered layout: %+v", snapshot.Rooms)
	}
	text := strings.Join(snapshot.ASCII(0, false), "\n")
	if !strings.Contains(text, "[@?tower") || !strings.Contains(text, "? = not explored yet") {
		test.Fatal(text)
	}
}
