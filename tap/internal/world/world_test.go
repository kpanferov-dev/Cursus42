package world

import (
	"path/filepath"
	"testing"
)

func sample(test *testing.T) *Data {
	test.Helper()
	data, err := Load(filepath.Join("..", "..", "world", "world.json"))
	if err != nil {
		test.Fatal(err)
	}
	return data
}
func TestWorldConstraints(test *testing.T) {
	data := sample(test)
	if len(data.Rooms) < 8 || len(data.Items) < 4 || len(data.NPCs) < 3 || len(data.Quests) < 2 {
		test.Fatalf("inadequate world: %+v", data)
	}
	if len(data.Rooms["loc.forge"].Exits) != 1 {
		test.Fatal("optional branch is missing")
	}
	// The square / garden / forest / marsh / harbor / square circuit exists.
	path := []string{"loc.square", "loc.garden", "loc.forest", "loc.marsh", "loc.harbor", "loc.square"}
	for step := 0; step < len(path)-1; step++ {
		found := false
		for _, dest := range data.Rooms[path[step]].Exits {
			if dest == path[step+1] {
				found = true
			}
		}
		if !found {
			test.Fatalf("circuit broken: %s -> %s", path[step], path[step+1])
		}
	}
}
func TestWorldRejectsBadReferences(test *testing.T) {
	data := sample(test)
	room := data.Rooms[data.Start]
	room.Exits["north"] = "missing"
	data.Rooms[data.Start] = room
	if err := data.Validate(); err == nil {
		test.Fatal("invalid exit accepted")
	}
}
func TestWorldRejectsDuplicatedItems(test *testing.T) {
	data := sample(test)
	room := data.Rooms["loc.market"]
	room.Items = append(room.Items, "item.herbs")
	data.Rooms["loc.market"] = room
	if err := data.Validate(); err == nil {
		test.Fatal("duplicate item accepted")
	}
}
func TestWorldRejectsOverlappingMapPositions(test *testing.T) {
	data := sample(test)
	square, market := data.Rooms["loc.square"], data.Rooms["loc.market"]
	square.Map, market.Map = []int{5, 5}, []int{5, 5}
	data.Rooms["loc.square"], data.Rooms["loc.market"] = square, market
	if err := data.Validate(); err == nil {
		test.Fatal("overlapping map positions accepted")
	}
}
