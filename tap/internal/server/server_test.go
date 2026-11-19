package server

import (
	"bufio"
	"encoding/json"
	"io"
	"net"
	"path/filepath"
	"strings"
	"tap/internal/world"
	"testing"
	"time"
)

type peer struct {
	t      *testing.T
	conn   net.Conn
	reader *bufio.Reader
}

func (p *peer) send(line string) {
	p.t.Helper()
	if _, err := io.WriteString(p.conn, line+"\n"); err != nil {
		p.t.Fatal(err)
	}
}
func (p *peer) next() string {
	p.t.Helper()
	_ = p.conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	line, err := p.reader.ReadString('\n')
	if err != nil {
		p.t.Fatalf("read response: %v", err)
	}
	return strings.TrimSpace(line)
}
func (p *peer) ack() string {
	p.t.Helper()
	for i := 0; i < 30; i++ {
		line := p.next()
		if strings.HasPrefix(line, "OK") || strings.HasPrefix(line, "ERR ") {
			return line
		}
	}
	p.t.Fatal("too many async events")
	return ""
}
func (p *peer) command(line string) string { p.t.Helper(); p.send(line); return p.ack() }
func (p *peer) check(line, want string) string {
	p.t.Helper()
	got := p.command(line)
	if !strings.HasPrefix(got, want) {
		p.t.Fatalf("%q => %q, expected prefix %q", line, got, want)
	}
	return got
}
func launch(t *testing.T) (*Server, string) {
	t.Helper()
	w, err := world.Load(filepath.Join("..", "..", "world", "world.json"))
	if err != nil {
		t.Fatal(err)
	}
	s, err := New(w, io.Discard)
	if err != nil {
		t.Fatal(err)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	go func() { _ = s.Serve(ln) }()
	t.Cleanup(func() { _ = s.Close() })
	return s, ln.Addr().String()
}
func join(t *testing.T, addr, name string) *peer {
	t.Helper()
	conn, err := net.DialTimeout("tcp", addr, time.Second)
	if err != nil {
		t.Fatal(err)
	}
	p := &peer{t, conn, bufio.NewReader(conn)}
	t.Cleanup(func() { _ = conn.Close() })
	if got := p.next(); got != "OK hello proto=1" {
		t.Fatalf("bad greeting %q", got)
	}
	p.check("CONNECT "+name, "OK connected")
	return p
}
func TestTCPItemsProtocolAndDisconnect(t *testing.T) {
	_, addr := launch(t)
	a := join(t, addr, "alice")
	b := join(t, addr, "bob")
	a.check("WHO", "OK players=2")
	a.check("MOVE north", "OK room=loc.market")
	a.check("MOVE east", "OK room=loc.library")
	b.check("MOVE north", "OK room=loc.market")
	b.check("MOVE east", "OK room=loc.library")
	look := a.check("LOOK", "OK {")
	var state struct {
		Items   []string `json:"items"`
		Players []string `json:"players"`
	}
	if err := json.Unmarshal([]byte(strings.TrimPrefix(look, "OK ")), &state); err != nil {
		t.Fatal(err)
	}
	if len(state.Players) != 2 {
		t.Fatalf("room players %+v", state)
	}
	a.check("TAKE Silver Compass", "OK taken=item.silver_compass")
	b.check("TAKE item.silver_compass", "ERR 404 ITEM_NOT_FOUND")
	a.check("INVENTORY", "OK [\"item.silver_compass\"]")
	a.check("DROP item.silver_compass", "OK dropped=item.silver_compass")
	b.check("TAKE silver compass", "OK taken=item.silver_compass")
	a.check("DROP item.silver_compass", "ERR 404 ITEM_NOT_IN_INVENTORY")
	a.check("MOVE nowhere", "ERR 301 NO_EXIT")
	a.check("DOESNOTEXIST", "ERR 400 UNKNOWN_COMMAND")
	a.check("CHAT WRONG hello", "ERR 400 INVALID_SCOPE")
	// TCP coalescing: multiple complete commands in a single write.
	if _, err := io.WriteString(a.conn, "WHO\nSTATUS\n"); err != nil {
		t.Fatal(err)
	}
	if got := a.ack(); got != "OK players=2" {
		t.Fatal(got)
	}
	if got := a.ack(); !strings.HasPrefix(got, "OK {\"hp\":") || !strings.Contains(got, "\"gold\":") {
		t.Fatal(got)
	}
	_ = b.conn.Close()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if a.check("WHO", "OK players=") == "OK players=1" {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	a.check("WHO", "OK players=1")
	a.check("LOOK", "OK {")
}
func TestQuestsCombatAndGroups(t *testing.T) {
	_, addr := launch(t)
	a := join(t, addr, "Akira")
	b := join(t, addr, "Bela")
	a.check("GROUP CREATE", "OK group=grp.Akira")
	a.check("GROUP INVITE Bela", "OK")
	b.check("GROUP JOIN Akira", "OK group=grp.Akira")
	a.check("CHAT GROUP Hello team", "OK")
	b.check("GROUP LEAVE", "OK")
	b.check("CHAT GROUP test", "ERR 401 NOT_IN_GROUP")
	a.check("QUEST Master Cartographer", "OK {")
	a.check("MOVE north", "OK room=loc.market")
	a.check("MOVE east", "OK room=loc.library")
	a.check("TAKE Silver Compass", "OK taken=item.silver_compass")
	a.check("MOVE west", "OK room=loc.market")
	a.check("MOVE south", "OK room=loc.square")
	a.check("TALK Master Cartographer", "OK Thank you!")
	journal := a.check("QUESTS", "OK [")
	if !strings.Contains(journal, `"quest_id":"quest.compass"`) || !strings.Contains(journal, `"status":"completed"`) {
		t.Fatal(journal)
	}
	a.check("QUEST Master Cartographer", "ERR 406 NO_QUEST_AVAILABLE")
	a.check("MOVE north", "OK room=loc.market")
	a.check("MOVE east", "OK room=loc.library")
	a.check("MOVE east", "OK room=loc.tower")
	a.check("QUEST Marsh Ranger", "OK {")
	a.check("MOVE south", "OK room=loc.forest")
	a.check("MOVE south", "OK room=loc.marsh")
	for i := 0; i < 3; i++ {
		got := a.check("ATTACK Marsh Wraith", "OK {")
		if i == 2 && !strings.Contains(got, `"status":"victory"`) {
			t.Fatal(got)
		}
	}
	if got := a.check("STATUS", "OK {"); !strings.Contains(got, `"gold":75`) {
		t.Fatal(got)
	}
	if got := a.check("QUESTS", "OK ["); !strings.Contains(got, `"quest_id":"quest.wraith"`) || !strings.Contains(got, `"status":"completed"`) {
		t.Fatal(got)
	}
	a.check("ATTACK Marsh Wraith", "ERR 404 NPC_NOT_FOUND")
}
func TestAuthAndMalformed(t *testing.T) {
	_, addr := launch(t)
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	p := &peer{t, conn, bufio.NewReader(conn)}
	if p.next() != "OK hello proto=1" {
		t.Fatal("missing greeting")
	}
	p.check("LOOK", "ERR 403 AUTH_REQUIRED")
	p.check("CONNECT 测试者", "OK connected")
	a := join(t, addr, "Alice")
	got := a.check("CONNECT Alice", "ERR 400 ALREADY_CONNECTED")
	_ = got
	conn2, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	defer conn2.Close()
	b := &peer{t, conn2, bufio.NewReader(conn2)}
	b.next()
	b.check("CONNECT aLiCe", "ERR 201 NAME_IN_USE")
	b.check("CONNECT bad name", "ERR 400 INVALID_USERNAME")
	a.check("CHAT GLOBAL Hi 世界", "OK")
}
