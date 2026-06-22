# Pick a Python interpreter (prefer python3, fallback to python)
PYTHON ?= $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)

# Always use .venv in the project root
VENV_DIR := .venv
#VENV_PYTHON := $(VENV_DIR)/bin/python
#VENV_PIP    := $(VENV_DIR)/bin/pip
VENV_PYTHON := $(VENV_DIR)/Scripts/python
VENV_PIP    := $(VENV_DIR)/Scripts/pip

.PHONY: help install venv install-deps run debug lint lint-strict \
        clean clean-venv test info \
        run-easy1 run-easy2 run-easy3 \
        run-medium1 run-medium2 run-medium3 \
        run-hard1 run-hard2 run-hard3 run-challenger \
        run-all run-all-verbose

help:
	@echo "fly_in — Drone routing simulation"
	@echo ""
	@echo "Targets:"
	@echo "  install        Create venv at $(VENV_DIR) and install deps"
	@echo "  run MAP=path   Run a simulation (use ARGS=--visual for color)"
	@echo "  debug MAP=path Run inside pdb"
	@echo "  lint           flake8 + mypy"
	@echo "  lint-strict    flake8 + mypy --strict"
	@echo "  test           pytest"
	@echo "  clean          Remove __pycache__, .mypy_cache, etc."
	@echo "  clean-venv     Remove the virtualenv at $(VENV_DIR)"
	@echo "  info           Show detected paths"
	@echo ""

info:
	@echo "Python : $(PYTHON)"
	@echo "Venv   : $(VENV_DIR)"

# ── Installation ────────────────────────────────────────────────────────────

install: venv install-deps
	@echo ""
	@echo "Installation complete."
	@echo "  Activate with : source $(VENV_DIR)/bin/activate"
	@echo "  Or just use   : make run MAP=maps/01_linear_path.txt"

venv:
	@if [ -z "$(PYTHON)" ]; then \
	  echo "ERROR: No Python interpreter found. Install python3."; \
	  exit 1; \
	fi
	@if [ ! -d "$(VENV_DIR)" ]; then \
	  echo "Creating venv at $(VENV_DIR)"; \
	  mkdir -p "$(VENV_DIR)"; \
	  "$(PYTHON)" -m venv "$(VENV_DIR)"; \
	else \
	  echo "Venv already exists at $(VENV_DIR)"; \
	fi

install-deps:
	@echo "Upgrading pip"
	@"$(VENV_PYTHON)" -m pip install --upgrade pip --quiet
	@echo "Installing dependencies"
	@"$(VENV_PIP)" install --quiet flake8 mypy pytest
	@echo "Optional: matplotlib (for --graph)"
	@"$(VENV_PIP)" install --quiet matplotlib || \
	  echo "  (matplotlib skipped)"

# ── Running ─────────────────────────────────────────────────────────────────

run:
	@if [ -z "$(MAP)" ]; then \
	  echo "Usage: make run MAP=maps/01_linear_path.txt [ARGS=--visual]"; \
	  exit 1; \
	fi
	@if [ -x "$(VENV_PYTHON)" ]; then \
	  "$(VENV_PYTHON)" main.py "$(MAP)" $(ARGS); \
	else \
	  "$(PYTHON)" main.py "$(MAP)" $(ARGS); \
	fi

debug:
	@if [ -z "$(MAP)" ]; then \
	  echo "Usage: make debug MAP=maps/01_linear_path.txt"; \
	  exit 1; \
	fi
	@if [ -x "$(VENV_PYTHON)" ]; then \
	  "$(VENV_PYTHON)" -m pdb main.py "$(MAP)" $(ARGS); \
	else \
	  "$(PYTHON)" -m pdb main.py "$(MAP)" $(ARGS); \
	fi

# ── Linting ─────────────────────────────────────────────────────────────────

lint:
	@if [ -x "$(VENV_PYTHON)" ]; then PY="$(VENV_PYTHON)"; \
	 else PY="$(PYTHON)"; fi; \
	"$$PY" -m flake8 . && \
	"$$PY" -m mypy . \
	  --warn-return-any \
	  --warn-unused-ignores \
	  --ignore-missing-imports \
	  --disallow-untyped-defs \
	  --check-untyped-defs

lint-strict:
	@if [ -x "$(VENV_PYTHON)" ]; then PY="$(VENV_PYTHON)"; \
	 else PY="$(PYTHON)"; fi; \
	"$$PY" -m flake8 . && \
	"$$PY" -m mypy . --strict

# ── Testing ─────────────────────────────────────────────────────────────────

test:
	@if [ -x "$(VENV_PYTHON)" ]; then \
	  "$(VENV_PYTHON)" -m pytest tests/ -v; \
	else \
	  "$(PYTHON)" -m pytest tests/ -v; \
	fi

# ── Cleaning ────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	@echo "Cleaned project caches."

clean-venv:
	@if [ -d "$(VENV_DIR)" ]; then \
	  rm -rf "$(VENV_DIR)"; \
	  echo "Removed venv at $(VENV_DIR)"; \
	else \
	  echo "No venv to remove at $(VENV_DIR)"; \
	fi

# ── Convenience map runners ─────────────────────────────────────────────────

run-easy1:
	@$(MAKE) run MAP=maps/01_linear_path.txt ARGS=--visual

run-easy2:
	@$(MAKE) run MAP=maps/02_simple_fork.txt ARGS=--visual

run-easy3:
	@$(MAKE) run MAP=maps/03_basic_capacity.txt ARGS=--visual

run-medium1:
	@$(MAKE) run MAP=maps/01_dead_end_trap.txt ARGS=--visual

run-medium2:
	@$(MAKE) run MAP=maps/02_circular_loop.txt ARGS=--visual

run-medium3:
	@$(MAKE) run MAP=maps/03_priority_puzzle.txt ARGS=--visual

run-hard1:
	@$(MAKE) run MAP=maps/01_maze_nightmare.txt ARGS=--visual

run-hard2:
	@$(MAKE) run MAP=maps/02_capacity_hell.txt ARGS=--visual

run-hard3:
	@$(MAKE) run MAP=maps/03_ultimate_challenge.txt ARGS=--visual

run-challenger:
	@$(MAKE) run MAP=maps/01_the_impossible_dream.txt ARGS=--visual

run-all:
	@if [ -x "$(VENV_PYTHON)" ]; then PY="$(VENV_PYTHON)"; \
	 else PY="$(PYTHON)"; fi; \
	for m in maps/*.txt; do \
	  printf "\n=== %s ===\n" "$$m"; \
	  TURNS=$$("$$PY" main.py "$$m" --quiet | wc -l); \
	  printf "  Solved in %s turns\n" "$$TURNS"; \
	done

run-all-verbose:
	@for m in maps/*.txt; do \
	  printf "\n=== %s ===\n" "$$m"; \
	  $(MAKE) -s run MAP="$$m"; \
	done