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

func (session *Session) Close() { session.once.Do(func() { _ = session.Conn.Close() }) }

// Send writes one command line. quiet commands (automatic GUI refreshes) are
// still matched with their reply but produce no narration message.
func (session *Session) Send(line string, quiet bool) error {
	if len(line) == 0 || len(line) > 1024 || strings.ContainsAny(line, "\r\n") || !utf8.ValidString(line) {
		return errors.New("invalid TAP line")
	}
	session.mu.Lock()
	defer session.mu.Unlock()
	if err := session.Conn.SetWriteDeadline(time.Now().Add(5 * time.Second)); err != nil {
		return err
	}
	session.Narrator.Expect(line, quiet)
	if _, err := io.WriteString(session.Conn, line+"\n"); err != nil {
		session.Narrator.Cancel()
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
func (session *Session) push(kind, data string) bool {
	select {
	case session.Messages <- Event{kind, data}:
		return true
	default:
		return false
	}
}
func (hub *Hub) register(session *Session) error {
	hub.mu.Lock()
	defer hub.mu.Unlock()
	if len(hub.sessions) >= 64 {
		return errors.New("GUI session limit reached")
	}
	hub.sessions[session.ID] = session
	return nil
}
func (hub *Hub) get(id string) *Session {
	hub.mu.Lock()
	defer hub.mu.Unlock()
	return hub.sessions[id]
}
func (hub *Hub) discard(id string) {
	hub.mu.Lock()
	session := hub.sessions[id]
	delete(hub.sessions, id)
	hub.mu.Unlock()
	if session != nil {
		session.Close()
	}
}
func (hub *Hub) readLoop(session *Session) {
	defer close(session.Messages)
	defer hub.discard(session.ID)
	for {
		line, err := session.Reader.ReadString('\n')
		if err != nil {
			// The connection has ended; SSE ends after this final notification.
			session.push("narration", "The connection to the server was lost.")
			session.push("", "ERR 900 CONNECTION_FAILED")
			return
		}
		line = strings.TrimSuffix(strings.TrimSuffix(line, "\n"), "\r")
		// Narration is queued first so it is delivered before a raw "OK bye"
		// makes the browser close its event stream.
		if text, ok := session.Narrator.Narrate(line); ok && !session.push("narration", text) {
			return
		}
		if !session.push("", line) {
			// Do not allow a slow browser to make a TCP reader block indefinitely.
			return
		}
		if changed, _ := session.Map.Observe(line); changed && !session.push("map", session.Map.JSON()) {
			return
		}
		if line == "OK bye" {
			return
		}
	}
}
func writeJSON(writer http.ResponseWriter, status int, value any) {
	writer.Header().Set("Content-Type", "application/json; charset=utf-8")
	writer.WriteHeader(status)
	_ = json.NewEncoder(writer).Encode(value)
}
func decodeJSON(request *http.Request, value any) error {
	defer request.Body.Close()
	return json.NewDecoder(io.LimitReader(request.Body, 4096)).Decode(value)
}
func (hub *Hub) HandleConnect(writer http.ResponseWriter, httpRequest *http.Request) {
	if httpRequest.Method != http.MethodPost {
		http.Error(writer, "POST only", 405)
		return
	}
	var request struct {
		Name string `json:"name"`
	}
	if err := decodeJSON(httpRequest, &request); err != nil {
		writeJSON(writer, 400, map[string]string{"error": err.Error()})
		return
	}
	if request.Name == "" || len(request.Name) > 128 || strings.ContainsAny(request.Name, "\n\r \t") {
		writeJSON(writer, 400, map[string]string{"error": "invalid username"})
		return
	}
	conn, err := net.DialTimeout("tcp", hub.ServerAddr, 4*time.Second)
	if err != nil {
		writeJSON(writer, 502, map[string]string{"error": "ERR 900 CONNECTION_FAILED: " + err.Error()})
		return
	}
	reader := bufio.NewReader(conn)
	_ = conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	hello, err := reader.ReadString('\n')
	if err != nil || strings.TrimSpace(hello) != "OK hello proto=1" {
		conn.Close()
		writeJSON(writer, 502, map[string]string{"error": "invalid TAP greeting"})
		return
	}
	_, err = io.WriteString(conn, "CONNECT "+request.Name+"\n")
	if err != nil {
		conn.Close()
		writeJSON(writer, 502, map[string]string{"error": err.Error()})
		return
	}
	line, err := reader.ReadString('\n')
	if err != nil {
		conn.Close()
		writeJSON(writer, 502, map[string]string{"error": "CONNECT: " + err.Error()})
		return
	}
	if strings.TrimSpace(line) != "OK connected" {
		conn.Close()
		explain := narrator.New(hub.Catalog, "")
		explain.SetGreeted()
		explain.Expect("CONNECT "+request.Name, false)
		message, _ := explain.Narrate(line)
		writeJSON(writer, 409, map[string]string{"error": strings.TrimSpace(line), "message": message})
		return
	}
	_ = conn.SetReadDeadline(time.Time{})
	key := make([]byte, 20)
	if _, err := rand.Read(key); err != nil {
		conn.Close()
		writeJSON(writer, 500, map[string]string{"error": err.Error()})
		return
	}
	story := narrator.New(hub.Catalog, request.Name)
	story.SetGreeted()
	position := worldmap.New(hub.Catalog)
	position.Observe("OK connected") // the greeting reply was consumed above
	session := &Session{ID: hex.EncodeToString(key), Conn: conn, Reader: reader, Messages: make(chan Event, 768), Narrator: story, Map: position}
	session.push("narration", fmt.Sprintf("Welcome, %s! You have entered the shared world.", request.Name))
	session.push("map", position.JSON())
	if err := hub.register(session); err != nil {
		conn.Close()
		writeJSON(writer, 503, map[string]string{"error": err.Error()})
		return
	}
	go hub.readLoop(session)
	writeJSON(writer, 200, map[string]string{"id": session.ID, "hello": "OK connected"})
}
func (hub *Hub) HandleSend(writer http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodPost {
		http.Error(writer, "POST only", 405)
		return
	}
	var req struct {
		ID    string `json:"id"`
		Line  string `json:"line"`
		Quiet bool   `json:"quiet"`
	}
	if err := decodeJSON(request, &req); err != nil {
		writeJSON(writer, 400, map[string]string{"error": err.Error()})
		return
	}
	session := hub.get(req.ID)
	if session == nil {
		writeJSON(writer, 404, map[string]string{"error": "session not found"})
		return
	}
	if err := session.Send(req.Line, req.Quiet); err != nil {
		writeJSON(writer, 502, map[string]string{"error": "ERR 901 SEND_FAILED: " + err.Error()})
		return
	}
	writeJSON(writer, 200, map[string]bool{"sent": true})
}
func (hub *Hub) HandleEvents(writer http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodGet {
		http.Error(writer, "GET only", 405)
		return
	}
	session := hub.get(request.URL.Query().Get("id"))
	if session == nil {
		http.Error(writer, "session not found", 404)
		return
	}
	flusher, ok := writer.(http.Flusher)
	if !ok {
		http.Error(writer, "SSE unsupported", 500)
		return
	}
	writer.Header().Set("Content-Type", "text/event-stream")
	writer.Header().Set("Cache-Control", "no-cache, no-store")
	writer.Header().Set("X-Accel-Buffering", "no")
	fmt.Fprint(writer, ": connected\n\n")
	flusher.Flush()
	ticker := time.NewTicker(15 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case ev, ok := <-session.Messages:
			if !ok {
				return
			}
			// TAP is line oriented; protect SSE protocol from injected line breaks.
			msg := strings.ReplaceAll(ev.Data, "\r", "")
			msg = strings.ReplaceAll(msg, "\n", "")
			if ev.Kind != "" {
				if _, err := fmt.Fprintf(writer, "event: %s\n", ev.Kind); err != nil {
					return
				}
			}
			if _, err := fmt.Fprintf(writer, "data: %s\n\n", msg); err != nil {
				return
			}
			flusher.Flush()
		case <-ticker.C:
			if _, err := fmt.Fprint(writer, ": keepalive\n\n"); err != nil {
				return
			}
			flusher.Flush()
		case <-request.Context().Done():
			return
		}
	}
}
func (hub *Hub) HandleClose(writer http.ResponseWriter, request *http.Request) {
	if request.Method != http.MethodPost {
		http.Error(writer, "POST only", 405)
		return
	}
	var req struct {
		ID string `json:"id"`
	}
	if err := decodeJSON(request, &req); err != nil {
		writeJSON(writer, 400, map[string]string{"error": err.Error()})
		return
	}
	hub.discard(req.ID)
	writeJSON(writer, 200, map[string]bool{"closed": true})
}
func (hub *Hub) Close() {
	hub.mu.Lock()
	sessions := hub.sessions
	hub.sessions = map[string]*Session{}
	hub.mu.Unlock()
	for _, session := range sessions {
		session.Close()
	}
}
