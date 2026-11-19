package main

import (
	"flag"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"
	"tap/internal/server"
	"tap/internal/world"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:4242", "TCP listen address")
	path := flag.String("world", "world/world.json", "world definition (JSON)")
	flag.Parse()
	data, err := world.Load(*path)
	if err != nil {
		log.Fatal(err)
	}
	s, err := server.New(data, os.Stderr)
	if err != nil {
		log.Fatal(err)
	}
	listener, err := net.Listen("tcp", *addr)
	if err != nil {
		log.Fatal(err)
	}
	fmt.Printf("TAP server listening on %s\n", listener.Addr().String())
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, os.Interrupt, syscall.SIGTERM)
	go func() { <-stop; _ = s.Close() }()
	if err := s.Serve(listener); err != nil {
		log.Fatal(err)
	}
}
