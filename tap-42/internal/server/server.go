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
	s := &Server{data: data, clients: map[*session]bool{}, names: map[string]*session{}, roomItems: map[string]map[string]bool{}, npcs: map[string]*npcState{}, groups: map[string]*group{}, logger: slog.New(slog.NewJSONHandler(logOutput, &slog.HandlerOptions{Level: slog.LevelInfo})), recentConnections: map[string][]time.Time{}, itemOrigin: map[string]string{}, rateLimit: 30}
	for id, room := range data.Rooms {
		s.roomItems[id] = map[string]bool{}
		for _, item := range room.Items {
			s.roomItems[id][item] = true
			s.itemOrigin[item] = id
		}
		for _, npc := range room.NPCs {
			s.npcs[npc] = &npcState{Room: id, HP: data.NPCs[npc].HP}
		}
	}
	return s, nil
}
func (s *Server) log(level slog.Level, event string, args ...any) {
	attrs := append([]any{"event", event}, args...)
	s.logger.Log(nil, level, event, attrs...)
}
func (s *Server) Serve(listener net.Listener) error {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return net.ErrClosed
	}
	s.listener = listener
	s.mu.Unlock()
	s.log(slog.LevelInfo, "listen", "addr", listener.Addr().String())
	for {
		conn, err := listener.Accept()
		if err != nil {
			s.mu.Lock()
			closed := s.closed
			s.mu.Unlock()
			if closed || errors.Is(err, net.ErrClosed) {
				return nil
			}
			s.log(slog.LevelError, "accept_failure", "error", err.Error())
			return err
		}
		s.mu.Lock()
		if s.closed || len(s.clients) >= maxClients {
			s.mu.Unlock()
			_, _ = io.WriteString(conn, "ERR 900 CONNECTION_FAILED\n")
			_ = conn.Close()
			continue
		}
		ip, _, err := net.SplitHostPort(conn.RemoteAddr().String())
		if err != nil {
			ip = conn.RemoteAddr().String()
		}
		now := time.Now()
		recent := s.recentConnections[ip]
		filtered := recent[:0]
		for _, t := range recent {
			if now.Sub(t) < time.Minute {
				filtered = append(filtered, t)
			}
		}
		if len(filtered) >= 15 {
			s.log(slog.LevelWarn, "rapid_connections", "ip", ip, "count_last_minute", len(filtered)+1)
		}
		s.recentConnections[ip] = append(filtered, now)
		c := &session{conn: conn, peer: conn.RemoteAddr().String(), outgoing: make(chan string, 128), inventory: map[string]bool{}, quests: map[string]*progress{}, invites: map[string]bool{}, unlocked: map[string]bool{}, talks: map[string]int{}, hp: maxHP}
		s.clients[c] = true
		s.log(slog.LevelInfo, "connection", "ip", c.peer)
		s.sendLocked(c, "OK hello proto=1")
		s.mu.Unlock()
		go s.writer(c)
		go s.reader(c)
	}
}
func (s *Server) Addr() string {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.listener == nil {
		return ""
	}
	return s.listener.Addr().String()
}
func (s *Server) Close() error {
	s.mu.Lock()
	if s.closed {
		s.mu.Unlock()
		return nil
	}
	s.closed = true
	listener := s.listener
	for c := range s.clients {
		s.removeLocked(c)
	}
	s.mu.Unlock()
	if listener != nil {
		return listener.Close()
	}
	return nil
}
func (s *Server) writer(c *session) {
	defer c.conn.Close()
	for line := range c.outgoing {
		_ = c.conn.SetWriteDeadline(time.Now().Add(5 * time.Second))
		if _, err := io.WriteString(c.conn, line+"\n"); err != nil {
			s.mu.Lock()
			name := c.name
			s.mu.Unlock()
			s.log(slog.LevelError, "send_failure", "ip", c.peer, "player", name, "error", err.Error(), "code", 901)
			return
		}
	}
}
func (s *Server) reader(c *session) {
	defer func() { s.mu.Lock(); s.removeLocked(c); s.mu.Unlock() }()
	scanner := bufio.NewScanner(c.conn)
	scanner.Buffer(make([]byte, 2048), maxLineBytes+1024)
	for scanner.Scan() {
		line := strings.TrimSuffix(scanner.Text(), "\r")
		s.mu.Lock()
		if c.closed {
			s.mu.Unlock()
			return
		}
		if len(line) > maxLineBytes || !utf8.ValidString(line) || badControl(line) {
			s.log(slog.LevelWarn, "malformed_input", "ip", c.peer, "player", c.name)
			s.sendLocked(c, "ERR 400 BAD_REQUEST")
			s.mu.Unlock()
			continue
		}
		if now := time.Now(); true {
			if now.Sub(c.rateStart) > time.Second {
				c.rateStart = now
				c.rateCount = 0
			}
			c.rateCount++
			if c.rateCount > s.rateLimit {
				if c.rateCount == s.rateLimit+1 {
					s.log(slog.LevelWarn, "command_flood", "ip", c.peer, "player", c.name, "rate", c.rateCount)
				}
				s.sendLocked(c, "ERR 429 RATE_LIMITED")
				s.mu.Unlock()
				continue
			}
		}
		keep := s.commandLocked(c, line)
		s.mu.Unlock()
		if !keep {
			return
		}
	}
	if err := scanner.Err(); err != nil {
		s.log(slog.LevelWarn, "read_failure", "ip", c.peer, "player", c.name, "error", err.Error())
	}
}
func badControl(s string) bool {
	for _, r := range s {
		if unicode.IsControl(r) {
			return true
		}
	}
	return false
}
func (s *Server) sendLocked(c *session, line string) {
	if c.closed {
		return
	}
	select {
	case c.outgoing <- line:
		s.log(slog.LevelInfo, "send", "player", c.name, "ip", c.peer, "message", line)
	default:
		s.log(slog.LevelWarn, "slow_client", "player", c.name, "ip", c.peer)
		// Closing this socket is safe while holding the state mutex.
		_ = c.conn.Close()
	}
}
func (s *Server) reply(c *session, line string) { s.sendLocked(c, line) }
func (s *Server) err(c *session, code int, message string) {
	s.sendLocked(c, fmt.Sprintf("ERR %03d %s", code, message))
}
func (s *Server) allLocked(line string) {
	for c := range s.clients {
		if c.name != "" {
			s.sendLocked(c, line)
		}
	}
}
func (s *Server) roomLocked(room, line string) {
	for c := range s.clients {
		if c.name != "" && c.room == room {
			s.sendLocked(c, line)
		}
	}
}
func (s *Server) groupLocked(g *group, line string) {
	for c := range g.Members {
		s.sendLocked(c, line)
	}
}
func (s *Server) statsLocked() { s.allLocked(fmt.Sprintf("EVT STATS players=%d", len(s.names))) }
func (s *Server) removeLocked(c *session) {
	if c.closed {
		return
	}
	if c.name != "" {
		delete(s.names, strings.ToLower(c.name))
		if c.group != "" {
			s.leaveGroupLocked(c)
		}
		// Retain item uniqueness if the owner disconnects unexpectedly.
		for item := range c.inventory {
			s.roomItems[c.room][item] = true
			s.roomLocked(c.room, fmt.Sprintf("EVT ROOM ITEM DROP %s %s", c.name, item))
		}
	}
	delete(s.clients, c)
	c.closed = true
	close(c.outgoing)
	s.log(slog.LevelInfo, "disconnection", "player", c.name, "ip", c.peer)
	if c.name != "" {
		s.roomLocked(c.room, "EVT ROOM PRESENCE LEAVE "+c.name)
		s.statsLocked()
	}
}
func (s *Server) commandLocked(c *session, line string) bool {
	line = strings.TrimSpace(line)
	cmd, arg, _ := strings.Cut(line, " ")
	cmd = strings.ToUpper(cmd)
	arg = strings.TrimSpace(arg)
	s.log(slog.LevelInfo, "command", "player", c.name, "ip", c.peer, "command", cmd, "args", arg)
	if cmd == "CONNECT" {
		if c.name != "" {
			s.err(c, 400, "ALREADY_CONNECTED")
			return true
		}
		if !validName(arg) {
			s.err(c, 400, "INVALID_USERNAME")
			return true
		}
		if s.names[strings.ToLower(arg)] != nil {
			s.err(c, 201, "NAME_IN_USE")
			return true
		}
		c.name = arg
		c.room = s.data.Start
		s.names[strings.ToLower(c.name)] = c
		s.reply(c, "OK connected")
		if intro := s.data.Story.Intro; intro != "" {
			s.sendLocked(c, "EVT STORY INTRO "+intro) // extension: opening of the storyline
		}
		s.roomLocked(c.room, "EVT ROOM PRESENCE ENTER "+c.name)
		s.statsLocked()
		return true
	}
	if c.name == "" {
		s.err(c, 403, "AUTH_REQUIRED")
		return true
	}
	if cmd == "QUIT" {
		if arg != "" {
			s.err(c, 400, "BAD_REQUEST")
			return true
		}
		s.reply(c, "OK bye")
		return false
	}
	switch cmd {
	case "LOOK", "INVENTORY", "WHO", "STATUS", "QUESTS":
		if arg != "" {
			s.err(c, 400, "BAD_REQUEST")
			break
		}
		switch cmd {
		case "LOOK":
			s.reply(c, "OK "+jsonLine(s.lookLocked(c)))
		case "INVENTORY":
			s.reply(c, "OK "+jsonLine(world.SortedKeys(c.inventory)))
		case "WHO":
			s.reply(c, fmt.Sprintf("OK players=%d", len(s.names)))
		case "STATUS":
			// Struct keeps the RFC field order (hp, max_hp, status) before the extensions.
			s.reply(c, "OK "+jsonLine(struct {
				HP      int    `json:"hp"`
				MaxHP   int    `json:"max_hp"`
				Status  string `json:"status"`
				Gold    int    `json:"gold"`
				Attack  int    `json:"attack"`
				Defense int    `json:"defense"`
				Victory bool   `json:"victory"`
			}{c.hp, maxHP, s.statusLocked(c), c.gold, s.attackPowerLocked(c), s.defenseLocked(c), c.victory}))
		case "QUESTS":
			s.reply(c, "OK "+jsonLine(s.questsLocked(c)))
		}
	case "MOVE":
		s.moveLocked(c, arg)
	case "CHAT":
		s.chatLocked(c, arg)
	case "TAKE":
		s.takeLocked(c, arg)
	case "DROP":
		s.dropLocked(c, arg)
	case "TALK":
		s.talkLocked(c, arg)
	case "ATTACK":
		s.attackLocked(c, arg)
	case "USE":
		s.useLocked(c, arg)
	case "DEFEND":
		s.defendLocked(c, arg)
	case "FLEE":
		s.fleeLocked(c, arg)
	case "QUEST":
		s.questLocked(c, arg)
	case "GROUP":
		s.groupCommandLocked(c, arg)
	default:
		s.err(c, 400, "UNKNOWN_COMMAND")
	}
	return true
}
func validName(name string) bool {
	if name == "" || utf8.RuneCountInString(name) > 32 {
		return false
	}
	for _, r := range name {
		if !unicode.IsLetter(r) && !unicode.IsDigit(r) && r != '_' && r != '-' {
			return false
		}
	}
	return true
}
func jsonLine(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return "null"
	}
	return string(b)
}
func (s *Server) statusLocked(c *session) string {
	if c.combat != "" {
		return "combat"
	}
	if c.hp < 50 {
		return "wounded"
	}
	return "healthy"
}
func (s *Server) lookLocked(c *session) any {
	r := s.data.Rooms[c.room]
	players := []string{}
	for other := range s.clients {
		if other.name != "" && other.room == c.room {
			players = append(players, other.name)
		}
	}
	sort.Strings(players)
	items := world.SortedKeys(s.roomItems[c.room])
	npcs := []string{}
	for _, id := range r.NPCs {
		if s.npcs[id].HP > 0 {
			npcs = append(npcs, id)
		}
	}
	sort.Strings(npcs)
	return map[string]any{"room": map[string]any{"id": c.room, "name": r.Name, "description": r.Description, "exits": r.Exits}, "players": players, "items": items, "npcs": npcs}
}
func (s *Server) moveLocked(c *session, arg string) {
	if arg == "" || strings.Contains(arg, " ") {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	if c.combat != "" {
		s.err(c, 400, "IN_COMBAT_USE_FLEE")
		return
	}
	dir := strings.ToLower(arg)
	newRoom, ok := s.data.Rooms[c.room].Exits[dir]
	if !ok {
		s.err(c, 301, "NO_EXIT")
		return
	}
	opened := ""
	if key := s.data.Rooms[c.room].Locks[dir]; key != "" && !c.unlocked[c.room+">"+dir] {
		if !c.inventory[key] {
			s.err(c, 302, "EXIT_LOCKED") // extension: an item is needed to open it
			return
		}
		// The door stays open for this player even after the item is given away.
		c.unlocked[c.room+">"+dir] = true
		opened = key
	}
	old := c.room
	c.room = newRoom
	s.reply(c, "OK room="+newRoom)
	if opened != "" {
		s.sendLocked(c, fmt.Sprintf("EVT PLAYER UNLOCK %s %s", dir, opened))
		s.log(slog.LevelInfo, "unlock", "player", c.name, "room", old, "direction", dir, "item", opened)
	}
	s.roomLocked(old, "EVT ROOM PRESENCE LEAVE "+c.name)
	s.roomLocked(newRoom, "EVT ROOM PRESENCE ENTER "+c.name)
	s.log(slog.LevelInfo, "movement", "player", c.name, "from", old, "to", newRoom)
}
func (s *Server) chatLocked(c *session, arg string) {
	scope, msg, ok := strings.Cut(arg, " ")
	scope = strings.ToUpper(scope)
	msg = strings.TrimSpace(msg)
	if !ok || msg == "" || len(msg) > 800 {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	switch scope {
	case "GLOBAL":
		s.reply(c, "OK")
		s.allLocked("EVT GLOBAL CHAT " + c.name + " " + msg)
	case "ROOM":
		s.reply(c, "OK")
		s.roomLocked(c.room, "EVT ROOM CHAT "+c.name+" "+msg)
	case "GROUP":
		if c.group == "" {
			s.err(c, 401, "NOT_IN_GROUP")
			return
		}
		s.reply(c, "OK")
		s.groupLocked(s.groups[c.group], "EVT GROUP CHAT "+c.name+" "+msg)
	default:
		s.err(c, 400, "INVALID_SCOPE")
	}
}
func (s *Server) matchItem(ids map[string]bool, name string) string {
	for _, id := range world.SortedKeys(ids) {
		item := s.data.Items[id]
		if strings.EqualFold(name, id) || strings.EqualFold(name, item.Name) || strings.EqualFold(name, strings.TrimPrefix(id, "item.")) {
			return id
		}
	}
	return ""
}
func (s *Server) takeLocked(c *session, arg string) {
	if arg == "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	id := s.matchItem(s.roomItems[c.room], arg)
	if id == "" || !s.data.Items[id].Obtainable {
		s.err(c, 404, "ITEM_NOT_FOUND")
		return
	}
	if len(c.inventory) >= maxInventory {
		s.err(c, 400, "INVENTORY_FULL")
		return
	}
	delete(s.roomItems[c.room], id)
	c.inventory[id] = true
	s.reply(c, "OK taken="+id)
	s.roomLocked(c.room, fmt.Sprintf("EVT ROOM ITEM TAKE %s %s", c.name, id))
	s.log(slog.LevelInfo, "item_take", "player", c.name, "room", c.room, "item", id)
}
func (s *Server) dropLocked(c *session, arg string) {
	if arg == "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	id := s.matchItem(c.inventory, arg)
	if id == "" {
		s.err(c, 404, "ITEM_NOT_IN_INVENTORY")
		return
	}
	delete(c.inventory, id)
	s.roomItems[c.room][id] = true
	s.reply(c, "OK dropped="+id)
	s.roomLocked(c.room, fmt.Sprintf("EVT ROOM ITEM DROP %s %s", c.name, id))
	s.log(slog.LevelInfo, "item_drop", "player", c.name, "room", c.room, "item", id)
}
func (s *Server) findNPCLocked(c *session, arg string) string {
	for _, id := range s.data.Rooms[c.room].NPCs {
		n := s.data.NPCs[id]
		if s.npcs[id].HP > 0 && (strings.EqualFold(id, arg) || strings.EqualFold(n.Name, arg) || strings.EqualFold(strings.TrimPrefix(id, "npc."), arg)) {
			return id
		}
	}
	return ""
}

// ---------------------------------------------------------------- storyline

// nextQuestLocked returns the first quest of an NPC the player has not
// completed yet; allDone is true when the NPC has quests and all are done.
func (s *Server) nextQuestLocked(c *session, npcID string) (questID string, allDone bool) {
	list := s.data.NPCs[npcID].QuestList()
	for _, id := range list {
		if p := c.quests[id]; p == nil || p.Status != "completed" {
			return id, false
		}
	}
	return "", len(list) > 0
}

func (s *Server) completedLocked(c *session, questID string) bool {
	p := c.quests[questID]
	return p != nil && p.Status == "completed"
}

// questReadyLocked reports whether every prerequisite quest is completed.
func (s *Server) questReadyLocked(c *session, questID string) bool {
	for _, req := range s.data.Quests[questID].Requires {
		if !s.completedLocked(c, req) {
			return false
		}
	}
	return true
}

// attackPowerLocked: base 14 + best carried weapon + permanent quest bonuses.
func (s *Server) attackPowerLocked(c *session) int {
	weapon, bonus := 0, 0
	for id := range c.inventory {
		weapon = max(weapon, s.data.Items[id].Attack)
	}
	for id, p := range c.quests {
		if p.Status == "completed" {
			bonus += s.data.Quests[id].RewardAttack
		}
	}
	return baseDamage + weapon + bonus
}

// defenseLocked: the best carried armour.
func (s *Server) defenseLocked(c *session) int {
	best := 0
	for id := range c.inventory {
		best = max(best, s.data.Items[id].Defense)
	}
	return best
}

// counterDamageLocked is the damage an NPC deals to the player (at least 1).
func (s *Server) counterDamageLocked(c *session, npcID string, halved bool) int {
	damage := s.data.NPCs[npcID].Attack - s.defenseLocked(c)
	if halved {
		damage = (damage + 1) / 2
	}
	return max(1, damage)
}

// itemExistsLocked reports whether an item is in some room or inventory.
func (s *Server) itemExistsLocked(id string) bool {
	for _, items := range s.roomItems {
		if items[id] {
			return true
		}
	}
	for c := range s.clients {
		if c.inventory[id] {
			return true
		}
	}
	return false
}

// returnItemLocked puts a consumed item back at its original spawn room
// (after delay), so every player can still finish the story. Items that are
// NPC loot instead drop again the next time that NPC is defeated.
func (s *Server) returnItemLocked(id string, delay time.Duration) {
	room := s.itemOrigin[id]
	if room == "" {
		return
	}
	restore := func() {
		if s.closed || s.itemExistsLocked(id) {
			return
		}
		s.roomItems[room][id] = true
		s.roomLocked(room, "EVT ROOM ITEM RESPAWN "+id)
		s.log(slog.LevelInfo, "item_respawn", "item", id, "room", room)
	}
	if delay <= 0 {
		restore()
		return
	}
	time.AfterFunc(delay, func() {
		s.mu.Lock()
		defer s.mu.Unlock()
		restore()
	})
}

func (s *Server) talkLocked(c *session, arg string) {
	if arg == "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	id := s.findNPCLocked(c, arg)
	if id == "" {
		s.err(c, 404, "NPC_NOT_FOUND")
		return
	}
	npc := s.data.NPCs[id]
	text := "..."
	if len(npc.Dialogue) > 0 {
		text = npc.Dialogue[0]
		if len(npc.QuestList()) == 0 {
			// NPCs without quests rotate through their lines (hints, rumours).
			text = npc.Dialogue[c.talks[id]%len(npc.Dialogue)]
			c.talks[id]++
		}
	}
	questID, allDone := s.nextQuestLocked(c, id)
	switch {
	case allDone:
		if len(npc.Dialogue) > 1 {
			text = npc.Dialogue[len(npc.Dialogue)-1]
		}
	case questID != "":
		q := s.data.Quests[questID]
		p := c.quests[questID]
		switch {
		case p == nil && s.questReadyLocked(c, questID):
			if q.Offer != "" {
				text = q.Offer
			}
			text += fmt.Sprintf(" (Type QUEST %s to accept \"%s\".)", npc.Name, q.Name)
		case p == nil:
			// Prerequisites missing: the default line hints at what to do first.
		case q.Kind == "deliver" && c.inventory[q.Target]:
			delete(c.inventory, q.Target) // consumed by the quest giver, never duplicated
			s.completeQuestLocked(c, questID)
			text = q.Complete
			if text == "" {
				text = fmt.Sprintf("Thank you! Quest %s complete. You earned %d gold.", q.Name, q.RewardGold)
			}
			s.log(slog.LevelInfo, "item_delivered", "player", c.name, "item", q.Target, "npc", id)
			s.returnItemLocked(q.Target, 0)
		case q.Reminder != "":
			text = q.Reminder
		case q.Kind == "deliver":
			text = "Bring me the item, then TALK to me again."
		default:
			text = "Come back when it is done."
		}
	}
	s.reply(c, "OK "+text)
	s.log(slog.LevelInfo, "npc_talk", "player", c.name, "npc", id, "dialogue", text)
}

func (s *Server) questLocked(c *session, arg string) {
	if arg == "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	id := s.findNPCLocked(c, arg)
	if id == "" {
		s.err(c, 404, "NPC_NOT_FOUND")
		return
	}
	questID, _ := s.nextQuestLocked(c, id)
	if questID == "" {
		// No quests, or every quest of this NPC is completed.
		s.err(c, 406, "NO_QUEST_AVAILABLE")
		return
	}
	q := s.data.Quests[questID]
	p := c.quests[questID]
	if p == nil {
		if !s.questReadyLocked(c, questID) {
			// The next chapter is not unlocked yet (TALK gives a hint).
			s.err(c, 406, "NO_QUEST_AVAILABLE")
			return
		}
		p = &progress{Status: "active"}
		c.quests[questID] = p
		s.log(slog.LevelInfo, "quest_started", "player", c.name, "quest", questID)
	}
	s.reply(c, "OK "+jsonLine(map[string]any{"quest_id": questID, "name": q.Name, "description": q.Description, "reward": rewardText(q), "status": p.Status}))
}

func rewardText(q world.Quest) string {
	text := fmt.Sprintf("%d gold, %d HP", q.RewardGold, q.RewardHP)
	if q.RewardAttack > 0 {
		text += fmt.Sprintf(", +%d attack", q.RewardAttack)
	}
	if q.Final {
		text += ", VICTORY"
	}
	return text
}

func (s *Server) questsLocked(c *session) any {
	list := []any{}
	for _, id := range world.SortedKeys(c.quests) {
		q := s.data.Quests[id]
		p := c.quests[id]
		progressStr := "0/1"
		if p.Status == "completed" {
			progressStr = "1/1"
		}
		list = append(list, map[string]any{"quest_id": id, "name": q.Name, "status": p.Status, "progress": progressStr, "description": q.Description, "final": q.Final})
	}
	return list
}

func (s *Server) completeQuestLocked(c *session, id string) {
	p := c.quests[id]
	if p == nil || p.Status != "active" {
		return
	}
	p.Status = "completed"
	p.Current = 1
	q := s.data.Quests[id]
	c.gold += q.RewardGold
	c.hp = min(maxHP, c.hp+q.RewardHP)
	s.log(slog.LevelInfo, "quest_completed", "player", c.name, "quest", id, "gold", q.RewardGold)
	// Extension event: clients that don't understand it may ignore the notification.
	s.sendLocked(c, "EVT QUEST COMPLETE "+id)
	if q.Final && !c.victory {
		c.victory = true
		s.log(slog.LevelInfo, "victory", "player", c.name, "quest", id)
		s.allLocked("EVT GLOBAL VICTORY " + c.name)
	}
}

func (s *Server) attackLocked(c *session, arg string) {
	if arg == "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	id := s.findNPCLocked(c, arg)
	if id == "" {
		s.err(c, 404, "NPC_NOT_FOUND")
		return
	}
	n := s.data.NPCs[id]
	if n.Role != "enemy" {
		s.err(c, 405, "NPC_NOT_HOSTILE")
		return
	}
	if c.combat != "" && c.combat != id {
		s.err(c, 400, "ALREADY_IN_COMBAT")
		return
	}
	if n.RequiresQuest != "" && !s.completedLocked(c, n.RequiresQuest) {
		// Extension: the enemy can't be harmed yet (e.g. the Warden needs starsteel).
		s.err(c, 405, "NPC_INVULNERABLE")
		return
	}
	c.combat = id
	// Deterministic turn: player first; surviving NPC immediately counterattacks.
	damage := s.attackPowerLocked(c)
	state := s.npcs[id]
	state.HP = max(0, state.HP-damage)
	counter := 0
	outcome := "combat"
	if state.HP == 0 {
		outcome = "victory"
		for other := range s.clients {
			if other.combat == id {
				other.combat = ""
				other.defended = false
			}
		}
		// Only the player landing the killing blow completes "defeat" quests.
		for _, qid := range world.SortedKeys(s.data.Quests) {
			if q := s.data.Quests[qid]; q.Kind == "defeat" && q.Target == id {
				if p := c.quests[qid]; p != nil && p.Status == "active" {
					s.completeQuestLocked(c, qid)
				}
			}
		}
		if n.Loot != "" && !s.itemExistsLocked(n.Loot) {
			s.roomItems[state.Room][n.Loot] = true
			s.roomLocked(state.Room, fmt.Sprintf("EVT ROOM ITEM LOOT %s %s", id, n.Loot))
			s.log(slog.LevelInfo, "loot", "npc", id, "item", n.Loot, "room", state.Room)
		}
		room := state.Room
		time.AfterFunc(npcRespawn, func() {
			s.mu.Lock()
			defer s.mu.Unlock()
			if s.closed {
				return
			}
			state.HP = n.HP
			s.roomLocked(room, "EVT ROOM NPC RESPAWN "+id)
			s.log(slog.LevelInfo, "npc_respawn", "npc", id, "room", room)
		})
	} else {
		counter = s.counterDamageLocked(c, id, c.defended)
		c.defended = false
		c.hp -= counter
		if c.hp <= 0 {
			outcome = "respawn"
			s.respawnLocked(c)
		}
	}
	s.reply(c, "OK "+jsonLine(map[string]any{"attacker_hp": c.hp, "target_hp": state.HP, "damage": damage, "counter_damage": counter, "status": outcome}))
	s.roomLocked(state.Room, fmt.Sprintf("EVT ROOM COMBAT %s %s damage=%d counter_damage=%d target_hp=%d status=%s", c.name, id, damage, counter, state.HP, outcome))
	s.log(slog.LevelInfo, "combat", "player", c.name, "npc", id, "damage", damage, "counter", counter, "npc_hp", state.HP, "player_hp", c.hp, "status", outcome)
}

func (s *Server) respawnLocked(c *session) {
	old := c.room
	c.room = s.data.Start
	c.hp = 35
	c.combat = ""
	c.defended = false
	s.roomLocked(old, "EVT ROOM PRESENCE LEAVE "+c.name)
	s.roomLocked(c.room, "EVT ROOM PRESENCE ENTER "+c.name)
	s.sendLocked(c, "EVT PLAYER RESPAWN room="+c.room+" hp=35")
	s.log(slog.LevelWarn, "player_respawn", "player", c.name, "from", old, "to", c.room)
}

func (s *Server) defendLocked(c *session, arg string) {
	if arg != "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	if c.combat == "" {
		s.err(c, 400, "NOT_IN_COMBAT")
		return
	}
	// A defensive turn: the NPC attacks for half damage instead of full damage.
	damage := s.counterDamageLocked(c, c.combat, true)
	c.hp -= damage
	c.defended = false
	if c.hp <= 0 {
		s.respawnLocked(c)
	}
	s.reply(c, "OK "+jsonLine(map[string]any{"status": s.statusLocked(c), "hp": c.hp, "damage_taken": damage, "defended": true}))
	s.roomLocked(c.room, fmt.Sprintf("EVT ROOM COMBAT %s DEFEND damage_taken=%d", c.name, damage))
	s.log(slog.LevelInfo, "defend", "player", c.name, "damage_taken", damage)
}

// useLocked consumes a healing item. In combat it costs a turn: the enemy hits back.
func (s *Server) useLocked(c *session, arg string) {
	if arg == "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	id := s.matchItem(c.inventory, arg)
	if id == "" {
		s.err(c, 404, "ITEM_NOT_IN_INVENTORY")
		return
	}
	item := s.data.Items[id]
	if item.Heal <= 0 {
		s.err(c, 400, "ITEM_NOT_USABLE")
		return
	}
	delete(c.inventory, id)
	before := c.hp
	c.hp = min(maxHP, c.hp+item.Heal)
	healed := c.hp - before
	counter := 0
	if c.combat != "" {
		counter = s.counterDamageLocked(c, c.combat, false)
		c.hp -= counter
		if c.hp <= 0 {
			s.respawnLocked(c)
		}
	}
	s.reply(c, "OK "+jsonLine(map[string]any{"used": id, "healed": healed, "hp": c.hp, "counter_damage": counter}))
	s.log(slog.LevelInfo, "item_use", "player", c.name, "item", id, "healed", healed, "counter", counter)
	s.returnItemLocked(id, itemRegrow)
}

func (s *Server) fleeLocked(c *session, arg string) {
	if arg != "" {
		s.err(c, 400, "BAD_REQUEST")
		return
	}
	if c.combat == "" {
		s.err(c, 400, "NOT_IN_COMBAT")
		return
	}
	old := c.room
	c.combat = ""
	c.defended = false
	c.room = s.data.Start
	s.reply(c, "OK room="+c.room)
	s.roomLocked(old, "EVT ROOM PRESENCE LEAVE "+c.name)
	s.roomLocked(c.room, "EVT ROOM PRESENCE ENTER "+c.name)
	s.log(slog.LevelInfo, "flee", "player", c.name, "from", old)
}
func (s *Server) groupCommandLocked(c *session, arg string) {
	sub, rest, _ := strings.Cut(strings.TrimSpace(arg), " ")
	sub = strings.ToUpper(sub)
	rest = strings.TrimSpace(rest)
	switch sub {
	case "CREATE":
		if rest != "" {
			s.err(c, 400, "BAD_REQUEST")
			return
		}
		if c.group != "" {
			s.err(c, 402, "ALREADY_IN_GROUP")
			return
		}
		id := "grp." + c.name
		g := &group{ID: id, Leader: c.name, Members: map[*session]bool{c: true}}
		s.groups[id] = g
		c.group = id
		s.reply(c, "OK group="+id)
		s.log(slog.LevelInfo, "group_created", "player", c.name, "group", id)
	case "INVITE":
		if rest == "" {
			s.err(c, 400, "BAD_REQUEST")
			return
		}
		if c.group == "" {
			s.err(c, 401, "NOT_IN_GROUP")
			return
		}
		target := s.names[strings.ToLower(rest)]
		if target == nil {
			s.err(c, 404, "PLAYER_NOT_FOUND")
			return
		}
		if target.group != "" {
			s.err(c, 402, "ALREADY_IN_GROUP")
			return
		}
		target.invites[c.group] = true
		s.reply(c, "OK")
		s.sendLocked(target, "EVT GROUP INVITE "+s.groups[c.group].Leader)
		s.log(slog.LevelInfo, "group_invite", "from", c.name, "to", target.name, "group", c.group)
	case "JOIN":
		if rest == "" {
			s.err(c, 400, "BAD_REQUEST")
			return
		}
		if c.group != "" {
			s.err(c, 402, "ALREADY_IN_GROUP")
			return
		}
		leader := s.names[strings.ToLower(rest)]
		if leader == nil || leader.group == "" {
			s.err(c, 404, "GROUP_NOT_FOUND")
			return
		}
		g := s.groups[leader.group]
		if g == nil || !strings.EqualFold(g.Leader, rest) {
			s.err(c, 404, "GROUP_NOT_FOUND")
			return
		}
		if !c.invites[g.ID] {
			s.err(c, 403, "INVITE_REQUIRED")
			return
		}
		delete(c.invites, g.ID)
		c.group = g.ID
		g.Members[c] = true
		s.reply(c, "OK group="+g.ID)
		s.groupLocked(g, "EVT GROUP JOIN "+c.name)
		s.log(slog.LevelInfo, "group_join", "player", c.name, "group", g.ID)
	case "LEAVE":
		if rest != "" {
			s.err(c, 400, "BAD_REQUEST")
			return
		}
		if c.group == "" {
			s.err(c, 401, "NOT_IN_GROUP")
			return
		}
		s.leaveGroupLocked(c)
		s.reply(c, "OK")
	default:
		s.err(c, 400, "BAD_REQUEST")
	}
}
func (s *Server) leaveGroupLocked(c *session) {
	g := s.groups[c.group]
	if g == nil {
		c.group = ""
		return
	}
	delete(g.Members, c)
	c.group = ""
	if len(g.Members) == 0 {
		delete(s.groups, g.ID)
	} else {
		if g.Leader == c.name {
			names := []string{}
			for m := range g.Members {
				names = append(names, m.name)
			}
			sort.Strings(names)
			g.Leader = names[0]
		}
		s.groupLocked(g, "EVT GROUP LEAVE "+c.name)
	}
	s.log(slog.LevelInfo, "group_leave", "player", c.name, "group", g.ID)
}
