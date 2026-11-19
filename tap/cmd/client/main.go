// TCP CLI client: raw RFC command mode (case-insensitive commands) with asynchronous reads.
//
// Every server line is printed verbatim and, below it, an English "activity"
// message produced by the shared narrator (disable with -narrate=false).
// A map of the world showing your position is pinned at the top of the
// terminal and redrawn whenever you move (-map=top, the default on a
// terminal), printed after each move (-map=inline) or hidden (-map=off).
// The local command MAP prints the map at any time; it is not sent to the server.
package main

import (
	"bufio"
	"flag"
	"fmt"
	"net"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"

	"tap/internal/narrator"
	"tap/internal/worldmap"
)

// screen serializes all terminal output and owns the pinned map area.
type screen struct {
	mu     sync.Mutex
	mode   string // "top", "inline" or "off"
	color  bool
	rows   int
	cols   int
	height int // lines currently reserved for the pinned map
	m      *worldmap.Map
}

func (s *screen) println(lines ...string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, line := range lines {
		fmt.Println(line)
	}
}

func (s *screen) mapLines(width int, color bool) []string {
	snap := s.m.Snapshot()
	return append([]string{snap.Header()}, snap.ASCII(width, color)...)
}

// printMap prints the map into the scrolling output (MAP command, inline mode).
func (s *screen) printMap() {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, line := range s.mapLines(s.cols, s.color) {
		fmt.Println(line)
	}
}

// redraw repaints the pinned map without disturbing the scrolling area.
func (s *screen) redraw() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.redrawLocked()
}

func (s *screen) redrawLocked() {
	if s.mode != "top" {
		return
	}
	lines := append(s.mapLines(s.cols, s.color), strings.Repeat("─", s.cols))
	if len(lines)+4 > s.rows {
		// Terminal too small for a pinned map: fall back to inline maps.
		s.mode, s.height = "inline", 0
		fmt.Print("\x1b[r\x1b[2J\x1b[H")
		fmt.Println("(terminal too small for the pinned map: the map is now printed after each move; type MAP to show it)")
		return
	}
	if len(lines) != s.height {
		// Reserve the top lines; the rest of the screen scrolls normally.
		fmt.Printf("\x1b[%d;%dr\x1b[%d;1H", len(lines)+1, s.rows, s.rows)
		s.height = len(lines)
	}
	var b strings.Builder
	b.WriteString("\x1b7") // save cursor
	for i, line := range lines {
		fmt.Fprintf(&b, "\x1b[%d;1H\x1b[2K%s", i+1, line)
	}
	b.WriteString("\x1b8") // restore cursor
	fmt.Print(b.String())
}

func (s *screen) start() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.mode == "top" {
		fmt.Print("\x1b[2J\x1b[H")
		s.redrawLocked()
	}
}

func (s *screen) resize() {
	rows, cols, ok := termSize()
	if !ok {
		return
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.mode != "top" {
		return
	}
	s.rows, s.cols, s.height = rows, cols, 0
	fmt.Print("\x1b[2J")
	s.redrawLocked()
}

// stop gives the whole terminal back to the shell.
func (s *screen) stop() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.mode == "top" {
		fmt.Printf("\x1b[r\x1b[%d;1H\n", s.rows)
		s.mode = "off"
	}
}

func main() {
	addr := flag.String("addr", "127.0.0.1:4242", "TAP server host:port")
	name := flag.String("name", "alice", "unique player username")
	worldPath := flag.String("world", "world/world.json", "optional world metadata used for English names and the map")
	narrate := flag.Bool("narrate", true, "print an English activity message for every action and event")
	raw := flag.Bool("raw", true, "print raw TAP protocol lines")
	mapMode := flag.String("map", "auto", "map display: auto, top (pinned), inline (after each move) or off")
	flag.Parse()

	catalog := narrator.LoadCatalog(*worldPath)
	story := narrator.New(catalog, "")
	scr := &screen{m: worldmap.New(catalog), mode: *mapMode}
	rows, cols, isTerm := termSize()
	switch scr.mode {
	case "auto":
		scr.mode = "inline"
		if isTerm {
			scr.mode = "top"
		}
	case "top":
		if !isTerm {
			scr.mode = "inline"
		}
	case "inline", "off":
	default:
		fmt.Fprintln(os.Stderr, "invalid -map value; use auto, top, inline or off")
		os.Exit(2)
	}
	scr.rows, scr.cols = rows, cols
	scr.color = isTerm && os.Getenv("NO_COLOR") == ""

	c, err := net.Dial("tcp", *addr)
	if err != nil {
		fmt.Fprintln(os.Stderr, "ERR 900 CONNECTION_FAILED:", err)
		os.Exit(1)
	}
	defer c.Close()
	scr.start()
	defer scr.stop()

	// Restore the terminal on Ctrl+C and redraw the map on resize.
	signals := make(chan os.Signal, 4)
	signal.Notify(signals, os.Interrupt, syscall.SIGTERM)
	notifyResize(signals)
	go func() {
		for sig := range signals {
			if sig == os.Interrupt || sig == syscall.SIGTERM {
				scr.stop()
				_ = c.Close()
				os.Exit(130)
			}
			scr.resize()
		}
	}()

	// sendLine registers the command with the narrator and writes it
	// atomically, so replies are always matched to the right command.
	var sendMu sync.Mutex
	sendLine := func(line string, quiet bool) error {
		sendMu.Lock()
		defer sendMu.Unlock()
		story.Expect(line, quiet)
		if _, err := fmt.Fprintln(c, line); err != nil {
			story.Cancel()
			return err
		}
		return nil
	}

	var once sync.Once
	done := make(chan struct{})
	go func() {
		sc := bufio.NewScanner(c)
		sc.Buffer(make([]byte, 1024), 64*1024)
		for sc.Scan() {
			line := strings.TrimSuffix(sc.Text(), "\r")
			text, ok, quiet := story.Describe(line)
			out := []string{}
			if !quiet && (*raw || !*narrate) {
				out = append(out, line)
			}
			if *narrate && ok {
				out = append(out, "  » "+text)
			}
			scr.println(out...)
			changed, moved := scr.m.Observe(line)
			if changed {
				scr.redraw()
			}
			if moved && scr.mode == "inline" {
				scr.printMap()
			}
			// In a world we don't know (another team's server), look around
			// automatically to discover the exits of the new room.
			unknownStart := line == "OK connected" && scr.m.Snapshot().Current == ""
			if unknownStart || (moved && !strings.HasPrefix(line, "OK {") && !scr.m.CurrentExplored()) {
				_ = sendLine("LOOK", true)
			}
			if line == "OK bye" {
				break
			}
		}
		if err := sc.Err(); err != nil {
			scr.println("ERR 900 CONNECTION_FAILED: " + err.Error())
			if *narrate {
				scr.println("  » The connection to the server was lost.")
			}
		}
		once.Do(func() { close(done) })
	}()

	if err := sendLine("CONNECT "+*name, false); err != nil {
		fmt.Fprintln(os.Stderr, "ERR 901 SEND_FAILED:", err)
		return
	}
	scr.println("Raw TAP commands: LOOK, MOVE north, TAKE Silver Compass, CHAT GLOBAL hello, QUIT  (local: MAP)")
	go func() {
		input := bufio.NewScanner(os.Stdin)
		for input.Scan() {
			line := strings.TrimSpace(input.Text())
			if line == "" {
				continue
			}
			if strings.EqualFold(line, "MAP") {
				// Local command: print the map, nothing is sent to the server.
				scr.printMap()
				continue
			}
			if err := sendLine(line, false); err != nil {
				scr.println("ERR 901 SEND_FAILED: " + err.Error())
				if *narrate {
					scr.println("  » Your command could not be sent to the server.")
				}
				_ = c.Close()
				return
			}
			if strings.EqualFold(line, "QUIT") {
				return
			}
		}
		// On stdin EOF, send QUIT instead of dropping queued responses.
		if err := sendLine("QUIT", false); err != nil {
			_ = c.Close()
		}
	}()
	<-done
}
