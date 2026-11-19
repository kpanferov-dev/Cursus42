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

func post(t *testing.T, url string, body any) map[string]any {
	t.Helper()
	b, _ := json.Marshal(body)
	res, err := http.Post(url, "application/json", bytes.NewReader(b))
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	var out map[string]any
	_ = json.NewDecoder(res.Body).Decode(&out)
	out["status"] = res.StatusCode
	return out
}

// End-to-end: real TAP TCP server -> HTTP bridge -> SSE narration events.
func TestBridgeNarratesActions(t *testing.T) {
	worldPath := filepath.Join("..", "..", "world", "world.json")
	data, err := world.Load(worldPath)
	if err != nil {
		t.Fatal(err)
	}
	srv, err := server.New(data, io.Discard)
	if err != nil {
		t.Fatal(err)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	go func() { _ = srv.Serve(ln) }()
	t.Cleanup(func() { _ = srv.Close() })

	hub := New(ln.Addr().String(), narrator.LoadCatalog(worldPath))
	t.Cleanup(hub.Close)
	mux := http.NewServeMux()
	mux.HandleFunc("/api/connect", hub.HandleConnect)
	mux.HandleFunc("/api/send", hub.HandleSend)
	mux.HandleFunc("/api/events", hub.HandleEvents)
	web := httptest.NewServer(mux)
	t.Cleanup(web.Close)

	conn := post(t, web.URL+"/api/connect", map[string]string{"name": "alice"})
	id, _ := conn["id"].(string)
	if id == "" {
		t.Fatalf("connect failed: %v", conn)
	}
	if dup := post(t, web.URL+"/api/connect", map[string]string{"name": "ALICE"}); dup["status"] != 409 || !strings.Contains(dup["message"].(string), "already taken") {
		t.Fatalf("duplicate name not explained: %v", dup)
	}

	res, err := http.Get(web.URL + "/api/events?id=" + id)
	if err != nil {
		t.Fatal(err)
	}
	defer res.Body.Close()
	narrations := make(chan string, 64)
	maps := make(chan string, 64)
	go func() {
		sc := bufio.NewScanner(res.Body)
		kind := ""
		for sc.Scan() {
			line := sc.Text()
			if k, ok := strings.CutPrefix(line, "event: "); ok {
				kind = k
			} else if d, ok := strings.CutPrefix(line, "data: "); ok {
				if kind == "narration" {
					narrations <- d
				} else if kind == "map" {
					maps <- d
				}
				kind = ""
			}
		}
		close(narrations)
	}()
	expect := func(want string) {
		t.Helper()
		timeout := time.After(3 * time.Second)
		for {
			select {
			case got, ok := <-narrations:
				if !ok {
					t.Fatalf("stream closed before %q", want)
				}
				if strings.Contains(got, want) {
					return
				}
			case <-timeout:
				t.Fatalf("no narration containing %q", want)
			}
		}
	}
	expect("Welcome, alice!")
	expect("At midnight the Great Clock")
	expectMap := func(want string) {
		t.Helper()
		timeout := time.After(3 * time.Second)
		for {
			select {
			case got := <-maps:
				var snap struct {
					Current string `json:"current"`
				}
				if err := json.Unmarshal([]byte(got), &snap); err != nil {
					t.Fatal(err)
				}
				if snap.Current == want {
					return
				}
			case <-timeout:
				t.Fatalf("no map event with current room %q", want)
			}
		}
	}
	expectMap("loc.square")
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "LOOK", "quiet": true})
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "TAKE Old Map Fragment"})
	expect("You pick up the Old Map Fragment.")
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "MOVE north"})
	expect("You head north and arrive at Moonlight Market.")
	expectMap("loc.market")
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "MOVE north"})
	expect("The way north is locked")
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "MOVE up"})
	expect(`You can't go "up" from here.`)
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "CHAT GLOBAL hello"})
	expect("You say to everyone: hello")
	post(t, web.URL+"/api/send", map[string]any{"id": id, "line": "QUIT"})
	expect("Goodbye!")
}
