package bridge

import (
	"bufio"
	"bytes"
	"encoding/json"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"tap/internal/narrator"
	"tap/internal/server"
	"tap/internal/world"
)

func post(test *testing.T, url string, body any) map[string]any {
	test.Helper()
	payload, _ := json.Marshal(body)
	res, err := http.Post(url, "application/json", bytes.NewReader(payload))
	if err != nil {
		test.Fatal(err)
	}
	defer res.Body.Close()
	var out map[string]any
	_ = json.NewDecoder(res.Body).Decode(&out)
	out["status"] = res.StatusCode
	return out
}

// End-to-end: real TAP TCP server -> HTTP bridge -> SSE narration events.
func TestBridgeNarratesActions(test *testing.T) {
	worldPath := filepath.Join("..", "..", "world", "world.json")
	data, err := world.Load(worldPath)
	if err != nil {
		test.Fatal(err)
	}
	srv, err := server.New(data, io.Discard)
	if err != nil {
		test.Fatal(err)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		test.Fatal(err)
	}
	go func() { _ = srv.Serve(ln) }()
	test.Cleanup(func() { _ = srv.Close() })

	hub := New(ln.Addr().String(), narrator.LoadCatalog(worldPath))
	test.Cleanup(hub.Close)
	mux := http.NewServeMux()
	mux.HandleFunc("/api/connect", hub.HandleConnect)
	mux.HandleFunc("/api/send", hub.HandleSend)
	mux.HandleFunc("/api/events", hub.HandleEvents)
	web := httptest.NewServer(mux)
	test.Cleanup(web.Close)

	conn := post(test, web.URL+"/api/connect", map[string]string{"name": "alice"})
	id, _ := conn["id"].(string)
	if id == "" {
		test.Fatalf("connect failed: %v", conn)
	}
	if dup := post(test, web.URL+"/api/connect", map[string]string{"name": "ALICE"}); dup["status"] != 409 || !strings.Contains(dup["message"].(string), "already taken") {
		test.Fatalf("duplicate name not explained: %v", dup)
	}

	res, err := http.Get(web.URL + "/api/events?id=" + id)
	if err != nil {
		test.Fatal(err)
	}
	defer res.Body.Close()
	narrations := make(chan string, 64)
	maps := make(chan string, 64)
	go func() {
		sc := bufio.NewScanner(res.Body)
		kind := ""
		for sc.Scan() {
			line := sc.Text()
			if eventKind, ok := strings.CutPrefix(line, "event: "); ok {
				kind = eventKind
			} else if eventData, ok := strings.CutPrefix(line, "data: "); ok {
				if kind == "narration" {
					narrations <- eventData
				} else if kind == "map" {
					maps <- eventData
				}
				kind = ""
			}
		}
		close(narrations)
	}()
	expect := func(want string) {
		test.Helper()
		timeout := time.After(3 * time.Second)
		for {
			select {
			case got, ok := <-narrations:
				if !ok {
					test.Fatalf("stream closed before %q", want)
				}
				if strings.Contains(got, want) {
					return
				}
			case <-timeout:
				test.Fatalf("no narration containing %q", want)
			}
		}
	}
	expect("Welcome, alice!")
	expect("At midnight the Great Clock")
	expectMap := func(want string) {
		test.Helper()
		timeout := time.After(3 * time.Second)
		for {
			select {
			case got := <-maps:
				var snap struct {
					Current string `json:"current"`
				}
				if err := json.Unmarshal([]byte(got), &snap); err != nil {
					test.Fatal(err)
				}
				if snap.Current == want {
					return
				}
			case <-timeout:
				test.Fatalf("no map event with current room %q", want)
			}
		}
	}
	expectMap("loc.square")
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "LOOK", "quiet": true})
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "TAKE Old Map Fragment"})
	expect("You pick up the Old Map Fragment.")
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "MOVE north"})
	expect("You head north and arrive at Moonlight Market.")
	expectMap("loc.market")
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "MOVE north"})
	expect("The way north is locked")
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "MOVE up"})
	expect(`You can't go "up" from here.`)
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "CHAT GLOBAL hello"})
	expect("You say to everyone: hello")
	post(test, web.URL+"/api/send", map[string]any{"id": id, "line": "QUIT"})
	expect("Goodbye!")
}
