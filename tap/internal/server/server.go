// Package server implements the authoritative multiplayer TAP world.
package server

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net"
	"sort"
	"strings"
	"sync"
	"time"
	"unicode"
	"unicode/utf8"

	"tap/internal/world"
)

const (
	maxClients   = 128
	maxLineBytes = 1024
	maxInventory = 32
	npcRespawn   = 25 * time.Second
	itemRegrow   = 30 * time.Second // consumed healing items grow back after this delay
	baseDamage   = 14
	maxHP        = 100
)

type progress struct {
	Status  string
	Current int
}
type npcState struct {
	Room string
	HP   int
}
type group struct {
	ID      string
	Leader  string
	Members map[*session]bool
}
type session struct {
	conn                      net.Conn
	outgoing                  chan string
	peer                      string
	closed                    bool
	name, room, group, combat string
	inventory                 map[string]bool
	quests                    map[string]*progress
	invites                   map[string]bool
	hp, gold                  int
	defended                  bool
	victory                   bool            // completed the final quest
	unlocked                  map[string]bool // "room>dir" doors this player has opened
	talks                     map[string]int  // dialogue rotation per NPC
	rateStart                 time.Time
	rateCount                 int
}

// Server serializes state changes under a mutex; socket writes happen in independent goroutines.
type Server struct {
	mu                sync.Mutex
	data              *world.Data
	clients           map[*session]bool
	names             map[string]*session
	roomItems         map[string]map[string]bool
	npcs              map[string]*npcState
	groups            map[string]*group
	logger            *slog.Logger
	listener          net.Listener
	closed            bool
	recentConnections map[string][]time.Time
	itemOrigin        map[string]string // item -> room where it first spawns
	rateLimit         int               // commands per second per client (anti-flood)
}

func New(data *world.Data, logOutput io.Writer) (*Server, error) {
	if err := data.Validate(); err != nil {
		return nil, err
	}
	if logOutput == nil {
		logOutput = io.Discard
	}
	server := &Server{data: data, clients: map[*session]bool{}, names: map[string]*session{}, roomItems: map[string]map[string]bool{}, npcs: map[string]*npcState{}, groups: map[string]*group{}, logger: slog.New(slog.NewJSONHandler(logOutput, &slog.HandlerOptions{Level: slog.LevelInfo})), recentConnections: map[string][]time.Time{}, itemOrigin: map[string]string{}, rateLimit: 30}
	for id, room := range data.Rooms {
		server.roomItems[id] = map[string]bool{}
		for _, item := range room.Items {
			server.roomItems[id][item] = true
			server.itemOrigin[item] = id
		}
		for _, npc := range room.NPCs {
			server.npcs[npc] = &npcState{Room: id, HP: data.NPCs[npc].HP}
		}
	}
	return server, nil
}
func (server *Server) log(level slog.Level, event string, args ...any) {
	attrs := append([]any{"event", event}, args...)
	server.logger.Log(nil, level, event, attrs...)
}
func (server *Server) Serve(listener net.Listener) error {
	server.mu.Lock()
	if server.closed {
		server.mu.Unlock()
		return net.ErrClosed
	}
	server.listener = listener
	server.mu.Unlock()
	server.log(slog.LevelInfo, "listen", "addr", listener.Addr().String())
	for {
		conn, err := listener.Accept()
		if err != nil {
			server.mu.Lock()
			closed := server.closed
			server.mu.Unlock()
			if closed || errors.Is(err, net.ErrClosed) {
				return nil
			}
			server.log(slog.LevelError, "accept_failure", "error", err.Error())
			return err
		}
		server.mu.Lock()
		if server.closed || len(server.clients) >= maxClients {
			server.mu.Unlock()
			_, _ = io.WriteString(conn, "ERR 900 CONNECTION_FAILED\n")
			_ = conn.Close()
			continue
		}
		ip, _, err := net.SplitHostPort(conn.RemoteAddr().String())
		if err != nil {
			ip = conn.RemoteAddr().String()
		}
		now := time.Now()
		recent := server.recentConnections[ip]
		filtered := recent[:0]
		for _, seen := range recent {
			if now.Sub(seen) < time.Minute {
				filtered = append(filtered, seen)
			}
		}
		if len(filtered) >= 15 {
			server.log(slog.LevelWarn, "rapid_connections", "ip", ip, "count_last_minute", len(filtered)+1)
		}
		server.recentConnections[ip] = append(filtered, now)
		client := &session{conn: conn, peer: conn.RemoteAddr().String(), outgoing: make(chan string, 128), inventory: map[string]bool{}, quests: map[string]*progress{}, invites: map[string]bool{}, unlocked: map[string]bool{}, talks: map[string]int{}, hp: maxHP}
		server.clients[client] = true
		server.log(slog.LevelInfo, "connection", "ip", client.peer)
		server.sendLocked(client, "OK hello proto=1")
		server.mu.Unlock()
		go server.writer(client)
		go server.reader(client)
	}
}
func (server *Server) Addr() string {
	server.mu.Lock()
	defer server.mu.Unlock()
	if server.listener == nil {
		return ""
	}
	return server.listener.Addr().String()
}
func (server *Server) Close() error {
	server.mu.Lock()
	if server.closed {
		server.mu.Unlock()
		return nil
	}
	server.closed = true
	listener := server.listener
	for client := range server.clients {
		server.removeLocked(client)
	}
	server.mu.Unlock()
	if listener != nil {
		return listener.Close()
	}
	return nil
}
func (server *Server) writer(client *session) {
	defer client.conn.Close()
	for line := range client.outgoing {
		_ = client.conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
		if _, err := io.WriteString(client.conn, line+"\n"); err != nil {
			server.mu.Lock()
			name := client.name
			server.mu.Unlock()
			server.log(slog.LevelError, "send_failure", "ip", client.peer, "player", name, "error", err.Error(), "code", 901)
			return
		}
	}
}
func (server *Server) reader(client *session) {
	defer func() { server.mu.Lock(); server.removeLocked(client); server.mu.Unlock() }()
	scanner := bufio.NewScanner(client.conn)
	scanner.Buffer(make([]byte, 2048), maxLineBytes+1024)
	for scanner.Scan() {
		line := strings.TrimSuffix(scanner.Text(), "\r")
		server.mu.Lock()
		if client.closed {
			server.mu.Unlock()
			return
		}
		if len(line) > maxLineBytes || !utf8.ValidString(line) || badControl(line) {
			server.log(slog.LevelWarn, "malformed_input", "ip", client.peer, "player", client.name)
			server.sendLocked(client, "ERR 400 BAD_REQUEST")
			server.mu.Unlock()
			continue
		}
		if now := time.Now(); true {
			if now.Sub(client.rateStart) > time.Second {
				client.rateStart = now
				client.rateCount = 0
			}
			client.rateCount++
			if client.rateCount > server.rateLimit {
				if client.rateCount == server.rateLimit+1 {
					server.log(slog.LevelWarn, "command_flood", "ip", client.peer, "player", client.name, "rate", client.rateCount)
				}
				server.sendLocked(client, "ERR 429 RATE_LIMITED")
				server.mu.Unlock()
				continue
			}
		}
		keep := server.commandLocked(client, line)
		server.mu.Unlock()
		if !keep {
			return
		}
	}
	if err := scanner.Err(); err != nil {
		server.log(slog.LevelWarn, "read_failure", "ip", client.peer, "player", client.name, "error", err.Error())
	}
}
func badControl(text string) bool {
	for _, char := range text {
		if unicode.IsControl(char) {
			return true
		}
	}
	return false
}
func (server *Server) sendLocked(client *session, line string) {
	if client.closed {
		return
	}
	select {
	case client.outgoing <- line:
		server.log(slog.LevelInfo, "send", "player", client.name, "ip", client.peer, "message", line)
	default:
		server.log(slog.LevelWarn, "slow_client", "player", client.name, "ip", client.peer)
		// Closing this socket is safe while holding the state mutex.
		_ = client.conn.Close()
	}
}
func (server *Server) reply(client *session, line string) { server.sendLocked(client, line) }
func (server *Server) err(client *session, code int, message string) {
	server.sendLocked(client, fmt.Sprintf("ERR %03d %s", code, message))
}
func (server *Server) allLocked(line string) {
	for client := range server.clients {
		if client.name != "" {
			server.sendLocked(client, line)
		}
	}
}
func (server *Server) roomLocked(room, line string) {
	for client := range server.clients {
		if client.name != "" && client.room == room {
			server.sendLocked(client, line)
		}
	}
}
func (server *Server) groupLocked(team *group, line string) {
	for client := range team.Members {
		server.sendLocked(client, line)
	}
}
func (server *Server) statsLocked() {
	server.allLocked(fmt.Sprintf("EVT STATS players=%d", len(server.names)))
}
func (server *Server) removeLocked(client *session) {
	if client.closed {
		return
	}
	if client.name != "" {
		delete(server.names, strings.ToLower(client.name))
		if client.group != "" {
			server.leaveGroupLocked(client)
		}
		// Retain item uniqueness if the owner disconnects unexpectedly.
		for item := range client.inventory {
			server.roomItems[client.room][item] = true
			server.roomLocked(client.room, fmt.Sprintf("EVT ROOM ITEM DROP %s %s", client.name, item))
		}
	}
	delete(server.clients, client)
	client.closed = true
	close(client.outgoing)
	server.log(slog.LevelInfo, "disconnection", "player", client.name, "ip", client.peer)
	if client.name != "" {
		server.roomLocked(client.room, "EVT ROOM PRESENCE LEAVE "+client.name)
		server.statsLocked()
	}
}
func (server *Server) commandLocked(client *session, line string) bool {
	line = strings.TrimSpace(line)
	cmd, arg, _ := strings.Cut(line, " ")
	cmd = strings.ToUpper(cmd)
	arg = strings.TrimSpace(arg)
	server.log(slog.LevelInfo, "command", "player", client.name, "ip", client.peer, "command", cmd, "args", arg)
	if cmd == "CONNECT" {
		if client.name != "" {
			server.err(client, 400, "ALREADY_CONNECTED")
			return true
		}
		if !validName(arg) {
			server.err(client, 400, "INVALID_USERNAME")
			return true
		}
		if server.names[strings.ToLower(arg)] != nil {
			server.err(client, 201, "NAME_IN_USE")
			return true
		}
		client.name = arg
		client.room = server.data.Start
		server.names[strings.ToLower(client.name)] = client
		server.reply(client, "OK connected")
		if intro := server.data.Story.Intro; intro != "" {
			server.sendLocked(client, "EVT STORY INTRO "+intro) // extension: opening of the storyline
		}
		server.roomLocked(client.room, "EVT ROOM PRESENCE ENTER "+client.name)
		server.statsLocked()
		return true
	}
	if client.name == "" {
		server.err(client, 403, "AUTH_REQUIRED")
		return true
	}
	if cmd == "QUIT" {
		if arg != "" {
			server.err(client, 400, "BAD_REQUEST")
			return true
		}
		server.reply(client, "OK bye")
		return false
	}
	switch cmd {
	case "LOOK", "INVENTORY", "WHO", "STATUS", "QUESTS":
		if arg != "" {
			server.err(client, 400, "BAD_REQUEST")
			break
		}
		switch cmd {
		case "LOOK":
			server.reply(client, "OK "+jsonLine(server.lookLocked(client)))
		case "INVENTORY":
			server.reply(client, "OK "+jsonLine(world.SortedKeys(client.inventory)))
		case "WHO":
			server.reply(client, fmt.Sprintf("OK players=%d", len(server.names)))
		case "STATUS":
			// Struct keeps the RFC field order (hp, max_hp, status) before the extensions.
			server.reply(client, "OK "+jsonLine(struct {
				HP      int    `json:"hp"`
				MaxHP   int    `json:"max_hp"`
				Status  string `json:"status"`
				Gold    int    `json:"gold"`
				Attack  int    `json:"attack"`
				Defense int    `json:"defense"`
				Victory bool   `json:"victory"`
			}{client.hp, maxHP, server.statusLocked(client), client.gold, server.attackPowerLocked(client), server.defenseLocked(client), client.victory}))
		case "QUESTS":
			server.reply(client, "OK "+jsonLine(server.questsLocked(client)))
		}
	case "MOVE":
		server.moveLocked(client, arg)
	case "CHAT":
		server.chatLocked(client, arg)
	case "TAKE":
		server.takeLocked(client, arg)
	case "DROP":
		server.dropLocked(client, arg)
	case "TALK":
		server.talkLocked(client, arg)
	case "ATTACK":
		server.attackLocked(client, arg)
	case "USE":
		server.useLocked(client, arg)
	case "DEFEND":
		server.defendLocked(client, arg)
	case "FLEE":
		server.fleeLocked(client, arg)
	case "QUEST":
		server.questLocked(client, arg)
	case "GROUP":
		server.groupCommandLocked(client, arg)
	default:
		server.err(client, 400, "UNKNOWN_COMMAND")
	}
	return true
}
func validName(name string) bool {
	if name == "" || utf8.RuneCountInString(name) > 32 {
		return false
	}
	for _, char := range name {
		if !unicode.IsLetter(char) && !unicode.IsDigit(char) && char != '_' && char != '-' {
			return false
		}
	}
	return true
}
func jsonLine(value any) string {
	encoded, err := json.Marshal(value)
	if err != nil {
		return "null"
	}
	return string(encoded)
}
func (server *Server) statusLocked(client *session) string {
	if client.combat != "" {
		return "combat"
	}
	if client.hp < 50 {
		return "wounded"
	}
	return "healthy"
}
func (server *Server) lookLocked(client *session) any {
	room := server.data.Rooms[client.room]
	players := []string{}
	for other := range server.clients {
		if other.name != "" && other.room == client.room {
			players = append(players, other.name)
		}
	}
	sort.Strings(players)
	items := world.SortedKeys(server.roomItems[client.room])
	npcs := []string{}
	for _, id := range room.NPCs {
		if server.npcs[id].HP > 0 {
			npcs = append(npcs, id)
		}
	}
	sort.Strings(npcs)
	return map[string]any{"room": map[string]any{"id": client.room, "name": room.Name, "description": room.Description, "exits": room.Exits}, "players": players, "items": items, "npcs": npcs}
}
func (server *Server) moveLocked(client *session, arg string) {
	if arg == "" || strings.Contains(arg, " ") {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	if client.combat != "" {
		server.err(client, 400, "IN_COMBAT_USE_FLEE")
		return
	}
	dir := strings.ToLower(arg)
	newRoom, ok := server.data.Rooms[client.room].Exits[dir]
	if !ok {
		server.err(client, 301, "NO_EXIT")
		return
	}
	opened := ""
	if key := server.data.Rooms[client.room].Locks[dir]; key != "" && !client.unlocked[client.room+">"+dir] {
		if !client.inventory[key] {
			server.err(client, 302, "EXIT_LOCKED") // extension: an item is needed to open it
			return
		}
		// The door stays open for this player even after the item is given away.
		client.unlocked[client.room+">"+dir] = true
		opened = key
	}
	old := client.room
	client.room = newRoom
	server.reply(client, "OK room="+newRoom)
	if opened != "" {
		server.sendLocked(client, fmt.Sprintf("EVT PLAYER UNLOCK %s %s", dir, opened))
		server.log(slog.LevelInfo, "unlock", "player", client.name, "room", old, "direction", dir, "item", opened)
	}
	server.roomLocked(old, "EVT ROOM PRESENCE LEAVE "+client.name)
	server.roomLocked(newRoom, "EVT ROOM PRESENCE ENTER "+client.name)
	server.log(slog.LevelInfo, "movement", "player", client.name, "from", old, "to", newRoom)
}
func (server *Server) chatLocked(client *session, arg string) {
	scope, msg, ok := strings.Cut(arg, " ")
	scope = strings.ToUpper(scope)
	msg = strings.TrimSpace(msg)
	if !ok || msg == "" || len(msg) > 800 {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	switch scope {
	case "GLOBAL":
		server.reply(client, "OK")
		server.allLocked("EVT GLOBAL CHAT " + client.name + " " + msg)
	case "ROOM":
		server.reply(client, "OK")
		server.roomLocked(client.room, "EVT ROOM CHAT "+client.name+" "+msg)
	case "GROUP":
		if client.group == "" {
			server.err(client, 401, "NOT_IN_GROUP")
			return
		}
		server.reply(client, "OK")
		server.groupLocked(server.groups[client.group], "EVT GROUP CHAT "+client.name+" "+msg)
	default:
		server.err(client, 400, "INVALID_SCOPE")
	}
}
func (server *Server) matchItem(ids map[string]bool, name string) string {
	for _, id := range world.SortedKeys(ids) {
		item := server.data.Items[id]
		if strings.EqualFold(name, id) || strings.EqualFold(name, item.Name) || strings.EqualFold(name, strings.TrimPrefix(id, "item.")) {
			return id
		}
	}
	return ""
}
func (server *Server) takeLocked(client *session, arg string) {
	if arg == "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	id := server.matchItem(server.roomItems[client.room], arg)
	if id == "" || !server.data.Items[id].Obtainable {
		server.err(client, 404, "ITEM_NOT_FOUND")
		return
	}
	if len(client.inventory) >= maxInventory {
		server.err(client, 400, "INVENTORY_FULL")
		return
	}
	delete(server.roomItems[client.room], id)
	client.inventory[id] = true
	server.reply(client, "OK taken="+id)
	server.roomLocked(client.room, fmt.Sprintf("EVT ROOM ITEM TAKE %s %s", client.name, id))
	server.log(slog.LevelInfo, "item_take", "player", client.name, "room", client.room, "item", id)
}
func (server *Server) dropLocked(client *session, arg string) {
	if arg == "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	id := server.matchItem(client.inventory, arg)
	if id == "" {
		server.err(client, 404, "ITEM_NOT_IN_INVENTORY")
		return
	}
	delete(client.inventory, id)
	server.roomItems[client.room][id] = true
	server.reply(client, "OK dropped="+id)
	server.roomLocked(client.room, fmt.Sprintf("EVT ROOM ITEM DROP %s %s", client.name, id))
	server.log(slog.LevelInfo, "item_drop", "player", client.name, "room", client.room, "item", id)
}
func (server *Server) findNPCLocked(client *session, arg string) string {
	for _, id := range server.data.Rooms[client.room].NPCs {
		npc := server.data.NPCs[id]
		if server.npcs[id].HP > 0 && (strings.EqualFold(id, arg) || strings.EqualFold(npc.Name, arg) || strings.EqualFold(strings.TrimPrefix(id, "npc."), arg)) {
			return id
		}
	}
	return ""
}

// ---------------------------------------------------------------- storyline

// nextQuestLocked returns the first quest of an NPC the player has not
// completed yet; allDone is true when the NPC has quests and all are done.
func (server *Server) nextQuestLocked(client *session, npcID string) (questID string, allDone bool) {
	list := server.data.NPCs[npcID].QuestList()
	for _, id := range list {
		if questProgress := client.quests[id]; questProgress == nil || questProgress.Status != "completed" {
			return id, false
		}
	}
	return "", len(list) > 0
}

func (server *Server) completedLocked(client *session, questID string) bool {
	questProgress := client.quests[questID]
	return questProgress != nil && questProgress.Status == "completed"
}

// questReadyLocked reports whether every prerequisite quest is completed.
func (server *Server) questReadyLocked(client *session, questID string) bool {
	for _, req := range server.data.Quests[questID].Requires {
		if !server.completedLocked(client, req) {
			return false
		}
	}
	return true
}

// attackPowerLocked: base 14 + best carried weapon + permanent quest bonuses.
func (server *Server) attackPowerLocked(client *session) int {
	weapon, bonus := 0, 0
	for id := range client.inventory {
		weapon = max(weapon, server.data.Items[id].Attack)
	}
	for id, questProgress := range client.quests {
		if questProgress.Status == "completed" {
			bonus += server.data.Quests[id].RewardAttack
		}
	}
	return baseDamage + weapon + bonus
}

// defenseLocked: the best carried armour.
func (server *Server) defenseLocked(client *session) int {
	best := 0
	for id := range client.inventory {
		best = max(best, server.data.Items[id].Defense)
	}
	return best
}

// counterDamageLocked is the damage an NPC deals to the player (at least 1).
func (server *Server) counterDamageLocked(client *session, npcID string, halved bool) int {
	damage := server.data.NPCs[npcID].Attack - server.defenseLocked(client)
	if halved {
		damage = (damage + 1) / 2
	}
	return max(1, damage)
}

// itemExistsLocked reports whether an item is in some room or inventory.
func (server *Server) itemExistsLocked(id string) bool {
	for _, items := range server.roomItems {
		if items[id] {
			return true
		}
	}
	for client := range server.clients {
		if client.inventory[id] {
			return true
		}
	}
	return false
}

// returnItemLocked puts a consumed item back at its original spawn room
// (after delay), so every player can still finish the story. Items that are
// NPC loot instead drop again the next time that NPC is defeated.
func (server *Server) returnItemLocked(id string, delay time.Duration) {
	room := server.itemOrigin[id]
	if room == "" {
		return
	}
	restore := func() {
		if server.closed || server.itemExistsLocked(id) {
			return
		}
		server.roomItems[room][id] = true
		server.roomLocked(room, "EVT ROOM ITEM RESPAWN "+id)
		server.log(slog.LevelInfo, "item_respawn", "item", id, "room", room)
	}
	if delay <= 0 {
		restore()
		return
	}
	time.AfterFunc(delay, func() {
		server.mu.Lock()
		defer server.mu.Unlock()
		restore()
	})
}

func (server *Server) talkLocked(client *session, arg string) {
	if arg == "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	id := server.findNPCLocked(client, arg)
	if id == "" {
		server.err(client, 404, "NPC_NOT_FOUND")
		return
	}
	npc := server.data.NPCs[id]
	text := "..."
	if len(npc.Dialogue) > 0 {
		text = npc.Dialogue[0]
		if len(npc.QuestList()) == 0 {
			// NPCs without quests rotate through their lines (hints, rumours).
			text = npc.Dialogue[client.talks[id]%len(npc.Dialogue)]
			client.talks[id]++
		}
	}
	questID, allDone := server.nextQuestLocked(client, id)
	switch {
	case allDone:
		if len(npc.Dialogue) > 1 {
			text = npc.Dialogue[len(npc.Dialogue)-1]
		}
	case questID != "":
		quest := server.data.Quests[questID]
		questProgress := client.quests[questID]
		switch {
		case questProgress == nil && server.questReadyLocked(client, questID):
			if quest.Offer != "" {
				text = quest.Offer
			}
			text += fmt.Sprintf(" (Type QUEST %s to accept \"%s\".)", npc.Name, quest.Name)
		case questProgress == nil:
			// Prerequisites missing: the default line hints at what to do first.
		case quest.Kind == "deliver" && client.inventory[quest.Target]:
			delete(client.inventory, quest.Target) // consumed by the quest giver, never duplicated
			server.completeQuestLocked(client, questID)
			text = quest.Complete
			if text == "" {
				text = fmt.Sprintf("Thank you! Quest %s complete. You earned %d gold.", quest.Name, quest.RewardGold)
			}
			server.log(slog.LevelInfo, "item_delivered", "player", client.name, "item", quest.Target, "npc", id)
			server.returnItemLocked(quest.Target, 0)
		case quest.Reminder != "":
			text = quest.Reminder
		case quest.Kind == "deliver":
			text = "Bring me the item, then TALK to me again."
		default:
			text = "Come back when it is done."
		}
	}
	server.reply(client, "OK "+text)
	server.log(slog.LevelInfo, "npc_talk", "player", client.name, "npc", id, "dialogue", text)
}

func (server *Server) questLocked(client *session, arg string) {
	if arg == "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	id := server.findNPCLocked(client, arg)
	if id == "" {
		server.err(client, 404, "NPC_NOT_FOUND")
		return
	}
	questID, _ := server.nextQuestLocked(client, id)
	if questID == "" {
		// No quests, or every quest of this NPC is completed.
		server.err(client, 406, "NO_QUEST_AVAILABLE")
		return
	}
	quest := server.data.Quests[questID]
	questProgress := client.quests[questID]
	if questProgress == nil {
		if !server.questReadyLocked(client, questID) {
			// The next chapter is not unlocked yet (TALK gives a hint).
			server.err(client, 406, "NO_QUEST_AVAILABLE")
			return
		}
		questProgress = &progress{Status: "active"}
		client.quests[questID] = questProgress
		server.log(slog.LevelInfo, "quest_started", "player", client.name, "quest", questID)
	}
	server.reply(client, "OK "+jsonLine(map[string]any{"quest_id": questID, "name": quest.Name, "description": quest.Description, "reward": rewardText(quest), "status": questProgress.Status}))
}

func rewardText(quest world.Quest) string {
	text := fmt.Sprintf("%d gold, %d HP", quest.RewardGold, quest.RewardHP)
	if quest.RewardAttack > 0 {
		text += fmt.Sprintf(", +%d attack", quest.RewardAttack)
	}
	if quest.Final {
		text += ", VICTORY"
	}
	return text
}

func (server *Server) questsLocked(client *session) any {
	list := []any{}
	for _, id := range world.SortedKeys(client.quests) {
		quest := server.data.Quests[id]
		questProgress := client.quests[id]
		progressStr := "0/1"
		if questProgress.Status == "completed" {
			progressStr = "1/1"
		}
		list = append(list, map[string]any{"quest_id": id, "name": quest.Name, "status": questProgress.Status, "progress": progressStr, "description": quest.Description, "final": quest.Final})
	}
	return list
}

func (server *Server) completeQuestLocked(client *session, id string) {
	questProgress := client.quests[id]
	if questProgress == nil || questProgress.Status != "active" {
		return
	}
	questProgress.Status = "completed"
	questProgress.Current = 1
	quest := server.data.Quests[id]
	client.gold += quest.RewardGold
	client.hp = min(maxHP, client.hp+quest.RewardHP)
	server.log(slog.LevelInfo, "quest_completed", "player", client.name, "quest", id, "gold", quest.RewardGold)
	// Extension event: clients that don't understand it may ignore the notification.
	server.sendLocked(client, "EVT QUEST COMPLETE "+id)
	if quest.Final && !client.victory {
		client.victory = true
		server.log(slog.LevelInfo, "victory", "player", client.name, "quest", id)
		server.allLocked("EVT GLOBAL VICTORY " + client.name)
	}
}

func (server *Server) attackLocked(client *session, arg string) {
	if arg == "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	id := server.findNPCLocked(client, arg)
	if id == "" {
		server.err(client, 404, "NPC_NOT_FOUND")
		return
	}
	npc := server.data.NPCs[id]
	if npc.Role != "enemy" {
		server.err(client, 405, "NPC_NOT_HOSTILE")
		return
	}
	if client.combat != "" && client.combat != id {
		server.err(client, 400, "ALREADY_IN_COMBAT")
		return
	}
	if npc.RequiresQuest != "" && !server.completedLocked(client, npc.RequiresQuest) {
		// Extension: the enemy can't be harmed yet (e.g. the Warden needs starsteel).
		server.err(client, 405, "NPC_INVULNERABLE")
		return
	}
	client.combat = id
	// Deterministic turn: player first; surviving NPC immediately counterattacks.
	damage := server.attackPowerLocked(client)
	state := server.npcs[id]
	state.HP = max(0, state.HP-damage)
	counter := 0
	outcome := "combat"
	if state.HP == 0 {
		outcome = "victory"
		for other := range server.clients {
			if other.combat == id {
				other.combat = ""
				other.defended = false
			}
		}
		// Only the player landing the killing blow completes "defeat" quests.
		for _, qid := range world.SortedKeys(server.data.Quests) {
			if quest := server.data.Quests[qid]; quest.Kind == "defeat" && quest.Target == id {
				if questProgress := client.quests[qid]; questProgress != nil && questProgress.Status == "active" {
					server.completeQuestLocked(client, qid)
				}
			}
		}
		if npc.Loot != "" && !server.itemExistsLocked(npc.Loot) {
			server.roomItems[state.Room][npc.Loot] = true
			server.roomLocked(state.Room, fmt.Sprintf("EVT ROOM ITEM LOOT %s %s", id, npc.Loot))
			server.log(slog.LevelInfo, "loot", "npc", id, "item", npc.Loot, "room", state.Room)
		}
		room := state.Room
		time.AfterFunc(npcRespawn, func() {
			server.mu.Lock()
			defer server.mu.Unlock()
			if server.closed {
				return
			}
			state.HP = npc.HP
			server.roomLocked(room, "EVT ROOM NPC RESPAWN "+id)
			server.log(slog.LevelInfo, "npc_respawn", "npc", id, "room", room)
		})
	} else {
		counter = server.counterDamageLocked(client, id, client.defended)
		client.defended = false
		client.hp -= counter
		if client.hp <= 0 {
			outcome = "respawn"
			server.respawnLocked(client)
		}
	}
	server.reply(client, "OK "+jsonLine(map[string]any{"attacker_hp": client.hp, "target_hp": state.HP, "damage": damage, "counter_damage": counter, "status": outcome}))
	server.roomLocked(state.Room, fmt.Sprintf("EVT ROOM COMBAT %s %s damage=%d counter_damage=%d target_hp=%d status=%s", client.name, id, damage, counter, state.HP, outcome))
	server.log(slog.LevelInfo, "combat", "player", client.name, "npc", id, "damage", damage, "counter", counter, "npc_hp", state.HP, "player_hp", client.hp, "status", outcome)
}

func (server *Server) respawnLocked(client *session) {
	old := client.room
	client.room = server.data.Start
	client.hp = 35
	client.combat = ""
	client.defended = false
	server.roomLocked(old, "EVT ROOM PRESENCE LEAVE "+client.name)
	server.roomLocked(client.room, "EVT ROOM PRESENCE ENTER "+client.name)
	server.sendLocked(client, "EVT PLAYER RESPAWN room="+client.room+" hp=35")
	server.log(slog.LevelWarn, "player_respawn", "player", client.name, "from", old, "to", client.room)
}

func (server *Server) defendLocked(client *session, arg string) {
	if arg != "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	if client.combat == "" {
		server.err(client, 400, "NOT_IN_COMBAT")
		return
	}
	// A defensive turn: the NPC attacks for half damage instead of full damage.
	damage := server.counterDamageLocked(client, client.combat, true)
	client.hp -= damage
	client.defended = false
	if client.hp <= 0 {
		server.respawnLocked(client)
	}
	server.reply(client, "OK "+jsonLine(map[string]any{"status": server.statusLocked(client), "hp": client.hp, "damage_taken": damage, "defended": true}))
	server.roomLocked(client.room, fmt.Sprintf("EVT ROOM COMBAT %s DEFEND damage_taken=%d", client.name, damage))
	server.log(slog.LevelInfo, "defend", "player", client.name, "damage_taken", damage)
}

// useLocked consumes a healing item. In combat it costs a turn: the enemy hits back.
func (server *Server) useLocked(client *session, arg string) {
	if arg == "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	id := server.matchItem(client.inventory, arg)
	if id == "" {
		server.err(client, 404, "ITEM_NOT_IN_INVENTORY")
		return
	}
	item := server.data.Items[id]
	if item.Heal <= 0 {
		server.err(client, 400, "ITEM_NOT_USABLE")
		return
	}
	delete(client.inventory, id)
	before := client.hp
	client.hp = min(maxHP, client.hp+item.Heal)
	healed := client.hp - before
	counter := 0
	if client.combat != "" {
		counter = server.counterDamageLocked(client, client.combat, false)
		client.hp -= counter
		if client.hp <= 0 {
			server.respawnLocked(client)
		}
	}
	server.reply(client, "OK "+jsonLine(map[string]any{"used": id, "healed": healed, "hp": client.hp, "counter_damage": counter}))
	server.log(slog.LevelInfo, "item_use", "player", client.name, "item", id, "healed", healed, "counter", counter)
	server.returnItemLocked(id, itemRegrow)
}

func (server *Server) fleeLocked(client *session, arg string) {
	if arg != "" {
		server.err(client, 400, "BAD_REQUEST")
		return
	}
	if client.combat == "" {
		server.err(client, 400, "NOT_IN_COMBAT")
		return
	}
	old := client.room
	client.combat = ""
	client.defended = false
	client.room = server.data.Start
	server.reply(client, "OK room="+client.room)
	server.roomLocked(old, "EVT ROOM PRESENCE LEAVE "+client.name)
	server.roomLocked(client.room, "EVT ROOM PRESENCE ENTER "+client.name)
	server.log(slog.LevelInfo, "flee", "player", client.name, "from", old)
}
func (server *Server) groupCommandLocked(client *session, arg string) {
	sub, rest, _ := strings.Cut(strings.TrimSpace(arg), " ")
	sub = strings.ToUpper(sub)
	rest = strings.TrimSpace(rest)
	switch sub {
	case "CREATE":
		if rest != "" {
			server.err(client, 400, "BAD_REQUEST")
			return
		}
		if client.group != "" {
			server.err(client, 402, "ALREADY_IN_GROUP")
			return
		}
		id := "grp." + client.name
		team := &group{ID: id, Leader: client.name, Members: map[*session]bool{client: true}}
		server.groups[id] = team
		client.group = id
		server.reply(client, "OK group="+id)
		server.log(slog.LevelInfo, "group_created", "player", client.name, "group", id)
	case "INVITE":
		if rest == "" {
			server.err(client, 400, "BAD_REQUEST")
			return
		}
		if client.group == "" {
			server.err(client, 401, "NOT_IN_GROUP")
			return
		}
		target := server.names[strings.ToLower(rest)]
		if target == nil {
			server.err(client, 404, "PLAYER_NOT_FOUND")
			return
		}
		if target.group != "" {
			server.err(client, 402, "ALREADY_IN_GROUP")
			return
		}
		target.invites[client.group] = true
		server.reply(client, "OK")
		server.sendLocked(target, "EVT GROUP INVITE "+server.groups[client.group].Leader)
		server.log(slog.LevelInfo, "group_invite", "from", client.name, "to", target.name, "group", client.group)
	case "JOIN":
		if rest == "" {
			server.err(client, 400, "BAD_REQUEST")
			return
		}
		if client.group != "" {
			server.err(client, 402, "ALREADY_IN_GROUP")
			return
		}
		leader := server.names[strings.ToLower(rest)]
		if leader == nil || leader.group == "" {
			server.err(client, 404, "GROUP_NOT_FOUND")
			return
		}
		team := server.groups[leader.group]
		if team == nil || !strings.EqualFold(team.Leader, rest) {
			server.err(client, 404, "GROUP_NOT_FOUND")
			return
		}
		if !client.invites[team.ID] {
			server.err(client, 403, "INVITE_REQUIRED")
			return
		}
		delete(client.invites, team.ID)
		client.group = team.ID
		team.Members[client] = true
		server.reply(client, "OK group="+team.ID)
		server.groupLocked(team, "EVT GROUP JOIN "+client.name)
		server.log(slog.LevelInfo, "group_join", "player", client.name, "group", team.ID)
	case "LEAVE":
		if rest != "" {
			server.err(client, 400, "BAD_REQUEST")
			return
		}
		if client.group == "" {
			server.err(client, 401, "NOT_IN_GROUP")
			return
		}
		server.leaveGroupLocked(client)
		server.reply(client, "OK")
	default:
		server.err(client, 400, "BAD_REQUEST")
	}
}
func (server *Server) leaveGroupLocked(client *session) {
	team := server.groups[client.group]
	if team == nil {
		client.group = ""
		return
	}
	delete(team.Members, client)
	client.group = ""
	if len(team.Members) == 0 {
		delete(server.groups, team.ID)
	} else {
		if team.Leader == client.name {
			names := []string{}
			for member := range team.Members {
				names = append(names, member.name)
			}
			sort.Strings(names)
			team.Leader = names[0]
		}
		server.groupLocked(team, "EVT GROUP LEAVE "+client.name)
	}
	server.log(slog.LevelInfo, "group_leave", "player", client.name, "group", team.ID)
}
