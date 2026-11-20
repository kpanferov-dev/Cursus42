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
	test   *testing.T
	conn   net.Conn
	reader *bufio.Reader
}

func (client *peer) send(line string) {
	client.test.Helper()
	if _, err := io.WriteString(client.conn, line+"\n"); err != nil {
		client.test.Fatal(err)
	}
}
func (client *peer) next() string {
	client.test.Helper()
	_ = client.conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	line, err := client.reader.ReadString('\n')
	if err != nil {
		client.test.Fatalf("read response: %v", err)
	}
	return strings.TrimSpace(line)
}
func (client *peer) ack() string {
	client.test.Helper()
	for attempt := 0; attempt < 30; attempt++ {
		line := client.next()
		if strings.HasPrefix(line, "OK") || strings.HasPrefix(line, "ERR ") {
			return line
		}
	}
	client.test.Fatal("too many async events")
	return ""
}
func (client *peer) command(line string) string {
	client.test.Helper()
	client.send(line)
	return client.ack()
}
func (client *peer) check(line, want string) string {
	client.test.Helper()
	got := client.command(line)
	if !strings.HasPrefix(got, want) {
		client.test.Fatalf("%q => %q, expected prefix %q", line, got, want)
	}
	return got
}
func launch(test *testing.T) (*Server, string) {
	test.Helper()
	loaded, err := world.Load(filepath.Join("..", "..", "world", "world.json"))
	if err != nil {
		test.Fatal(err)
	}
	server, err := New(loaded, io.Discard)
	if err != nil {
		test.Fatal(err)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		test.Fatal(err)
	}
	go func() { _ = server.Serve(ln) }()
	test.Cleanup(func() { _ = server.Close() })
	return server, ln.Addr().String()
}
func join(test *testing.T, addr, name string) *peer {
	test.Helper()
	conn, err := net.DialTimeout("tcp", addr, time.Second)
	if err != nil {
		test.Fatal(err)
	}
	client := &peer{test, conn, bufio.NewReader(conn)}
	test.Cleanup(func() { _ = conn.Close() })
	if got := client.next(); got != "OK hello proto=1" {
		test.Fatalf("bad greeting %q", got)
	}
	client.check("CONNECT "+name, "OK connected")
	return client
}
func TestTCPItemsProtocolAndDisconnect(test *testing.T) {
	_, addr := launch(test)
	alice := join(test, addr, "alice")
	bob := join(test, addr, "bob")
	alice.check("WHO", "OK players=2")
	alice.check("MOVE north", "OK room=loc.market")
	alice.check("MOVE east", "OK room=loc.library")
	bob.check("MOVE north", "OK room=loc.market")
	bob.check("MOVE east", "OK room=loc.library")
	look := alice.check("LOOK", "OK {")
	var state struct {
		Items   []string `json:"items"`
		Players []string `json:"players"`
	}
	if err := json.Unmarshal([]byte(strings.TrimPrefix(look, "OK ")), &state); err != nil {
		test.Fatal(err)
	}
	if len(state.Players) != 2 {
		test.Fatalf("room players %+v", state)
	}
	alice.check("TAKE Silver Compass", "OK taken=item.silver_compass")
	bob.check("TAKE item.silver_compass", "ERR 404 ITEM_NOT_FOUND")
	alice.check("INVENTORY", "OK [\"item.silver_compass\"]")
	alice.check("DROP item.silver_compass", "OK dropped=item.silver_compass")
	bob.check("TAKE silver compass", "OK taken=item.silver_compass")
	alice.check("DROP item.silver_compass", "ERR 404 ITEM_NOT_IN_INVENTORY")
	alice.check("MOVE nowhere", "ERR 301 NO_EXIT")
	alice.check("DOESNOTEXIST", "ERR 400 UNKNOWN_COMMAND")
	alice.check("CHAT WRONG hello", "ERR 400 INVALID_SCOPE")
	// TCP coalescing: multiple complete commands in a single write.
	if _, err := io.WriteString(alice.conn, "WHO\nSTATUS\n"); err != nil {
		test.Fatal(err)
	}
	if got := alice.ack(); got != "OK players=2" {
		test.Fatal(got)
	}
	if got := alice.ack(); !strings.HasPrefix(got, "OK {\"hp\":") || !strings.Contains(got, "\"gold\":") {
		test.Fatal(got)
	}
	_ = bob.conn.Close()
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if alice.check("WHO", "OK players=") == "OK players=1" {
			break
		}
		time.Sleep(10 * time.Millisecond)
	}
	alice.check("WHO", "OK players=1")
	alice.check("LOOK", "OK {")
}
func TestQuestsCombatAndGroups(test *testing.T) {
	_, addr := launch(test)
	akira := join(test, addr, "Akira")
	bela := join(test, addr, "Bela")
	akira.check("GROUP CREATE", "OK group=grp.Akira")
	akira.check("GROUP INVITE Bela", "OK")
	bela.check("GROUP JOIN Akira", "OK group=grp.Akira")
	akira.check("CHAT GROUP Hello team", "OK")
	bela.check("GROUP LEAVE", "OK")
	bela.check("CHAT GROUP test", "ERR 401 NOT_IN_GROUP")
	akira.check("QUEST Master Cartographer", "OK {")
	akira.check("MOVE north", "OK room=loc.market")
	akira.check("MOVE east", "OK room=loc.library")
	akira.check("TAKE Silver Compass", "OK taken=item.silver_compass")
	akira.check("MOVE west", "OK room=loc.market")
	akira.check("MOVE south", "OK room=loc.square")
	akira.check("TALK Master Cartographer", "OK Thank you!")
	journal := akira.check("QUESTS", "OK [")
	if !strings.Contains(journal, `"quest_id":"quest.compass"`) || !strings.Contains(journal, `"status":"completed"`) {
		test.Fatal(journal)
	}
	akira.check("QUEST Master Cartographer", "ERR 406 NO_QUEST_AVAILABLE")
	akira.check("MOVE north", "OK room=loc.market")
	akira.check("MOVE east", "OK room=loc.library")
	akira.check("MOVE east", "OK room=loc.tower")
	akira.check("QUEST Marsh Ranger", "OK {")
	akira.check("MOVE south", "OK room=loc.forest")
	akira.check("MOVE south", "OK room=loc.marsh")
	for turn := 0; turn < 3; turn++ {
		got := akira.check("ATTACK Marsh Wraith", "OK {")
		if turn == 2 && !strings.Contains(got, `"status":"victory"`) {
			test.Fatal(got)
		}
	}
	if got := akira.check("STATUS", "OK {"); !strings.Contains(got, `"gold":75`) {
		test.Fatal(got)
	}
	if got := akira.check("QUESTS", "OK ["); !strings.Contains(got, `"quest_id":"quest.wraith"`) || !strings.Contains(got, `"status":"completed"`) {
		test.Fatal(got)
	}
	akira.check("ATTACK Marsh Wraith", "ERR 404 NPC_NOT_FOUND")
}
func TestAuthAndMalformed(test *testing.T) {
	_, addr := launch(test)
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		test.Fatal(err)
	}
	defer conn.Close()
	anonymous := &peer{test, conn, bufio.NewReader(conn)}
	if anonymous.next() != "OK hello proto=1" {
		test.Fatal("missing greeting")
	}
	anonymous.check("LOOK", "ERR 403 AUTH_REQUIRED")
	anonymous.check("CONNECT 测试者", "OK connected")
	alice := join(test, addr, "Alice")
	got := alice.check("CONNECT Alice", "ERR 400 ALREADY_CONNECTED")
	_ = got
	conn2, err := net.Dial("tcp", addr)
	if err != nil {
		test.Fatal(err)
	}
	defer conn2.Close()
	second := &peer{test, conn2, bufio.NewReader(conn2)}
	second.next()
	second.check("CONNECT aLiCe", "ERR 201 NAME_IN_USE")
	second.check("CONNECT bad name", "ERR 400 INVALID_USERNAME")
	alice.check("CHAT GLOBAL Hi 世界", "OK")
}
