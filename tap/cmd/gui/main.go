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

// The browser client is split into plain HTML, CSS and JavaScript files,
// all embedded in the binary so the GUI needs no files at run time.
//
//go:embed ui.html
var homepage []byte

//go:embed ui.css
var uiCSS []byte

//go:embed ui.js
var uiJS []byte

// Scene view: illustrated room, characters and combat screen (original inline SVG art).
//
//go:embed scene.js
var sceneJS []byte

//go:embed scene.css
var sceneCSS []byte

func static(contentType string, body []byte) http.HandlerFunc {
	return func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Content-Type", contentType)
		_, _ = writer.Write(body)
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
	mux.HandleFunc("/", func(writer http.ResponseWriter, request *http.Request) {
		if request.URL.Path != "/" {
			http.NotFound(writer, request)
			return
		}
		writer.Header().Set("Content-Type", "text/html; charset=utf-8")
		_, _ = writer.Write(homepage)
	})
	mux.HandleFunc("/ui.css", static("text/css; charset=utf-8", uiCSS))
	mux.HandleFunc("/ui.js", static("text/javascript; charset=utf-8", uiJS))
	mux.HandleFunc("/scene.js", static("text/javascript; charset=utf-8", sceneJS))
	mux.HandleFunc("/scene.css", static("text/css; charset=utf-8", sceneCSS))
	mux.HandleFunc("/api/catalog", func(writer http.ResponseWriter, request *http.Request) {
		content, err := os.ReadFile(*worldPath)
		if err != nil {
			http.Error(writer, "world metadata unavailable", 404)
			return
		}
		writer.Header().Set("Content-Type", "application/json; charset=utf-8")
		_, _ = writer.Write(content)
	})
	mux.HandleFunc("/api/connect", hub.HandleConnect)
	mux.HandleFunc("/api/send", hub.HandleSend)
	mux.HandleFunc("/api/events", hub.HandleEvents)
	mux.HandleFunc("/api/close", hub.HandleClose)
	fmt.Printf("TAP GUI: http://%s (TCP upstream: %s)\n", *listen, *server)
	log.Fatal(http.ListenAndServe(*listen, mux))
}
