package world

import (
	"path/filepath"
	"testing"
)

func sample(t *testing.T) *Data {
	t.Helper()
	d, err := Load(filepath.Join("..", "..", "world", "world.json"))
	if err != nil {
		t.Fatal(err)
	}
	return d
}
func TestWorldConstraints(t *testing.T) {
	d := sample(t)
	if len(d.Rooms) < 8 || len(d.Items) < 4 || len(d.NPCs) < 3 || len(d.Quests) < 2 {
		t.Fatalf("inadequate world: %+v", d)
	}
	if len(d.Rooms["loc.forge"].Exits) != 1 {
		t.Fatal("optional branch is missing")
	}
	// The square / garden / forest / marsh / harbor / square circuit exists.
	path := []string{"loc.square", "loc.garden", "loc.forest", "loc.marsh", "loc.harbor", "loc.square"}
	for i := 0; i < len(path)-1; i++ {
		found := false
		for _, dest := range d.Rooms[path[i]].Exits {
			if dest == path[i+1] {
				found = true
			}
		}
		if !found {
			t.Fatalf("circuit broken: %s -> %s", path[i], path[i+1])
		}
	}
}
func TestWorldRejectsBadReferences(t *testing.T) {
	d := sample(t)
	r := d.Rooms[d.Start]
	r.Exits["north"] = "missing"
	d.Rooms[d.Start] = r
	if err := d.Validate(); err == nil {
		t.Fatal("invalid exit accepted")
	}
}
func TestWorldRejectsDuplicatedItems(t *testing.T) {
	d := sample(t)
	room := d.Rooms["loc.market"]
	room.Items = append(room.Items, "item.herbs")
	d.Rooms["loc.market"] = room
	if err := d.Validate(); err == nil {
		t.Fatal("duplicate item accepted")
	}
}
func TestWorldRejectsOverlappingMapPositions(t *testing.T) {
	d := sample(t)
	a, b := d.Rooms["loc.square"], d.Rooms["loc.market"]
	a.Map, b.Map = []int{5, 5}, []int{5, 5}
	d.Rooms["loc.square"], d.Rooms["loc.market"] = a, b
	if err := d.Validate(); err == nil {
		t.Fatal("overlapping map positions accepted")
	}
}
