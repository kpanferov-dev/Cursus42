.PHONY: install build run-server run-client run-client-gui lint format test test-race clean

GO ?= go
SERVER_ADDR ?= 127.0.0.1:4242
GUI_ADDR ?= 127.0.0.1:8080
NAME ?= player

install:
	$(GO) mod download

build:
	mkdir -p bin
	$(GO) build -o bin/tap-server ./cmd/server
	$(GO) build -o bin/tap-client ./cmd/client
	$(GO) build -o bin/tap-gui ./cmd/gui

run-server:
	$(GO) run ./cmd/server -addr $(SERVER_ADDR) -world world/world.json

run-client:
	$(GO) run ./cmd/client -addr $(SERVER_ADDR) -name $(NAME)

run-client-gui:
	$(GO) run ./cmd/gui -listen $(GUI_ADDR) -server $(SERVER_ADDR) -world world/world.json

lint:
	$(GO) vet ./...
	@test -z "$$(find cmd internal -name '*.go' -print0 | xargs -0 gofmt -l)" || { echo 'Run gofmt before committing'; exit 1; }

# Formats Go code with gofmt and the browser files with Prettier (needs Node.js; style in .prettierrc.json).
format:
	gofmt -w cmd internal
	npx --yes prettier@3 --write cmd/gui/*.html cmd/gui/*.css cmd/gui/*.js

test:
	$(GO) test ./...	

test-race:
	$(GO) test -race ./...

clean:
	rm -rf bin
