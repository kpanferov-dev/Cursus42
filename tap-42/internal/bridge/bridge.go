// Package bridge provides an HTTP/SSE gateway to a real TAP TCP connection.
// The gateway does not emulate the protocol: every browser has its own TCP session.
// Besides forwarding raw TAP lines, it attaches an English "narration" message
// (see package narrator) to every reply and event for the GUI activity chat,
// and a "map" event (see package worldmap) whenever the player's map changes.
package bridge

import (
	"bufio"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"strings"
	"sync"
	"time"
	"unicode/utf8"

	"tap/internal/narrator"
	"tap/internal/world"
	"tap/internal/worldmap"
)

// Event is one SSE message: Kind "" carries a raw TAP line, Kind "narration"
// the English description of what happened and Kind "map" a JSON map snapshot.
type Event struct {
	Kind string
	Data string
}

type Session struct {
	ID       string
	Conn     net.Conn
	Reader   *bufio.Reader
	Messages chan Event
	Narrator *narrator.Narrator
	Map      *worldmap.Map
	mu       sync.Mutex
	once     sync.Once
}

func (s *Session) Close() { s.once.Do(func() { _ = s.Conn.Close() }) }

// Send writes one command line. quiet commands (automatic GUI refreshes) are
// still matched with their reply but produce no narration message.
func (s *Session) Send(line string, quiet bool) error {
	if len(line) == 0 || len(line) > 1024 || strings.ContainsAny(line, "\r\n") || !utf8.ValidString(line) {
		return errors.New("invalid TAP line")
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if err := s.Conn.SetWriteDeadline(time.Now().Add(5 * time.Second)); err != nil {
		return err
	}
	s.Narrator.Expect(line, quiet)
	if _, err := io.WriteString(s.Conn, line+"\n"); err != nil {
		s.Narrator.Cancel()
		return err
	}
	return nil
}

type Hub struct {
	mu         sync.Mutex
	sessions   map[string]*Session
	ServerAddr string
	Catalog    *world.Data // optional display names for narration
}

func New(addr string, catalog *world.Data) *Hub {
	return &Hub{sessions: map[string]*Session{}, ServerAddr: addr, Catalog: catalog}
}

// push queues an event without ever blocking the TCP reader.
func (s *Session) push(kind, data string) bool {
	select {
	case s.Messages <- Event{kind, data}:
		return true
	default:
		return false
	}
}
func (h *Hub) register(s *Session) error {
	h.mu.Lock()
	defer h.mu.Unlock()
	if len(h.sessions) >= 64 {
		return errors.New("GUI session limit reached")
	}
	h.sessions[s.ID] = s
	return nil
}
func (h *Hub) get(id string) *Session { h.mu.Lock(); defer h.mu.Unlock(); return h.sessions[id] }
func (h *Hub) discard(id string) {
	h.mu.Lock()
	s := h.sessions[id]
	delete(h.sessions, id)
	h.mu.Unlock()
	if s != nil {
		s.Close()
	}
}
func (h *Hub) readLoop(s *Session) {
	defer close(s.Messages)
	defer h.discard(s.ID)
	for {
		line, err := s.Reader.ReadString('\n')
		if err != nil {
			// The connection has ended; SSE ends after this final notification.
			s.push("narration", "The connection to the server was lost.")
			s.push("", "ERR 900 CONNECTION_FAILED")
			return
		}
		line = strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")
		// Narration is queued first so it is delivered before a raw "OK bye"
		// makes the browser close its event stream.
		if text, ok := s.Narrator.Narrate(line); ok && !s.push("narration", text) {
			return
		}
		if !s.push("", line) {
			// Do not allow a slow browser to make a TCP reader block indefinitely.
			return
		}
		if changed, _ := s.Map.Observe(line); changed && !s.push("map", s.Map.JSON()) {
			return
		}
		if line == "OK bye" {
			return
		}
	}
}
func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func decodeJSON(r *http.Request, v any) error {
	defer r.Body.Close()
	return json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(v)
}
func (h *Hub) HandleConnect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	var request struct {
		Name string `json:"name"`
	}
	if err := decodeJSON(r, &request); err != nil {
		writeJSON(w, 400, map[string]string{"error": err.Error()})
		return
	}
	if request.Name == "" || len(request.Name) > 128 || strings.ContainsAny(request.Name, "\n\r \t") {
		writeJSON(w, 400, map[string]string{"error": "invalid username"})
		return
	}
	conn, err := net.DialTimeout("tcp", h.ServerAddr, 4*time.Second)
	if err != nil {
		writeJSON(w, 502, map[string]string{"error": "ERR 900 CONNECTION_FAILED: " + err.Error()})
		return
	}
	reader := bufio.NewReader(conn)
	_ = conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	hello, err := reader.ReadString('\n')
	if err != nil || strings.TrimSpace(hello) != "OK hello proto=1" {
		conn.Close()
		writeJSON(w, 502, map[string]string{"error": "invalid TAP greeting"})
		return
	}
	_, err = io.WriteString(conn, "CONNECT "+request.Name+"\n")
	if err != nil {
		conn.Close()
		writeJSON(w, 502, map[string]string{"error": err.Error()})
		return
	}
	line, err := reader.ReadString('\n')
	if err != nil {
		conn.Close()
		writeJSON(w, 502, map[string]string{"error": "CONNECT: " + err.Error()})
		return
	}
	if strings.TrimSpace(line) != "OK connected" {
		conn.Close()
		explain := narrator.New(h.Catalog, "")
		explain.SetGreeted()
		explain.Expect("CONNECT "+request.Name, false)
		message, _ := explain.Narrate(line)
		writeJSON(w, 409, map[string]string{"error": strings.TrimSpace(line), "message": message})
		return
	}
	_ = conn.SetReadDeadline(time.Time{})
	key := make([]byte, 20)
	if _, err := rand.Read(key); err != nil {
		conn.Close()
		writeJSON(w, 500, map[string]string{"error": err.Error()})
		return
	}
	story := narrator.New(h.Catalog, request.Name)
	story.SetGreeted()
	position := worldmap.New(h.Catalog)
	position.Observe("OK connected") // the greeting reply was consumed above
	s := &Session{ID: hex.EncodeToString(key), Conn: conn, Reader: reader, Messages: make(chan Event, 768), Narrator: story, Map: position}
	s.push("narration", fmt.Sprintf("Welcome, %s! You have entered the shared world.", request.Name))
	s.push("map", position.JSON())
	if err := h.register(s); err != nil {
		conn.Close()
		writeJSON(w, 503, map[string]string{"error": err.Error()})
		return
	}
	go h.readLoop(s)
	writeJSON(w, 200, map[string]string{"id": s.ID, "hello": "OK connected"})
}
func (h *Hub) HandleSend(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	var req struct {
		ID    string `json:"id"`
		Line  string `json:"line"`
		Quiet bool   `json:"quiet"`
	}
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, 400, map[string]string{"error": err.Error()})
		return
	}
	s := h.get(req.ID)
	if s == nil {
		writeJSON(w, 404, map[string]string{"error": "session not found"})
		return
	}
	if err := s.Send(req.Line, req.Quiet); err != nil {
		writeJSON(w, 502, map[string]string{"error": "ERR 901 SEND_FAILED: " + err.Error()})
		return
	}
	writeJSON(w, 200, map[string]bool{"sent": true})
}
func (h *Hub) HandleEvents(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "GET only", 405)
		return
	}
	s := h.get(r.URL.Query().Get("id"))
	if s == nil {
		http.Error(w, "session not found", 404)
		return
	}
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "SSE unsupported", 500)
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache, no-store")
	w.Header().Set("X-Accel-Buffering", "no")
	fmt.Fprint(w, ": connected\n\n")
	flusher.Flush()
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case ev, ok := <-s.Messages:
			if !ok {
				return
			}
			// TAP is line oriented; protect SSE protocol from injected line breaks.
			msg := strings.ReplaceAll(ev.Data, "\r", "")
			msg = strings.ReplaceAll(msg, "\n", "")
			if ev.Kind != "" {
				if _, err := fmt.Fprintf(w, "event: %s\n", ev.Kind); err != nil {
					return
				}
			}
			if _, err := fmt.Fprintf(w, "data: %s\n\n", msg); err != nil {
				return
			}
			flusher.Flush()
		case <-ticker.C:
			if _, err := fmt.Fprint(w, ": keepalive\n\n"); err != nil {
				return
			}
			flusher.Flush()
		case <-r.Context().Done():
			return
		}
	}
}
func (h *Hub) HandleClose(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", 405)
		return
	}
	var req struct {
		ID string `json:"id"`
	}
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, 400, map[string]string{"error": err.Error()})
		return
	}
	h.discard(req.ID)
	writeJSON(w, 200, map[string]bool{"closed": true})
}
func (h *Hub) Close() {
	h.mu.Lock()
	sessions := h.sessions
	h.sessions = map[string]*Session{}
	h.mu.Unlock()
	for _, s := range sessions {
		s.Close()
	}
}
