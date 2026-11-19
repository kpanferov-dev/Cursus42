package main

import (
	_ "embed"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"tap/internal/bridge"
	"tap/internal/narrator"
)

//go:embed ui.html
var homepage []byte

// Scene view: illustrated room, characters and combat screen (original inline SVG art).
//
//go:embed scene.js
var sceneJS []byte

//go:embed scene.css
var sceneCSS []byte

func static(contentType string, body []byte) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", contentType)
		_, _ = w.Write(body)
	}
}

func main() {
	listen := flag.String("listen", "127.0.0.1:8080", "HTTP GUI listen address")
	server := flag.String("server", "127.0.0.1:4242", "upstream TAP TCP server")
	worldPath := flag.String("world", "world/world.json", "local world metadata for GUI labels")
	flag.Parse()
	hub := bridge.New(*server, narrator.LoadCatalog(*worldPath))
	defer hub.Close()
	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = w.Write(homepage)
	})
	mux.HandleFunc("/scene.js", static("text/javascript; charset=utf-8", sceneJS))
	mux.HandleFunc("/scene.css", static("text/css; charset=utf-8", sceneCSS))
	mux.HandleFunc("/api/catalog", func(w http.ResponseWriter, r *http.Request) {
		b, err := os.ReadFile(*worldPath)
		if err != nil {
			http.Error(w, "world metadata unavailable", 404)
			return
		}
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		_, _ = w.Write(b)
	})
	mux.HandleFunc("/api/connect", hub.HandleConnect)
	mux.HandleFunc("/api/send", hub.HandleSend)
	mux.HandleFunc("/api/events", hub.HandleEvents)
	mux.HandleFunc("/api/close", hub.HandleClose)
	fmt.Printf("TAP GUI: http://%s (TCP upstream: %s)\n", *listen, *server)
	log.Fatal(http.ListenAndServe(*listen, mux))
}
