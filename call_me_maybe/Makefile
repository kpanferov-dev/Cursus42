.PHONY: install run debug clean lint lint-strict test visualize help

help:
	@echo "Targets:"
	@echo "  install      uv sync"
	@echo "  run          run the program with default paths"
	@echo "  debug        run under pdb"
	@echo "  clean        remove caches and output"
	@echo "  lint         flake8 + mypy (mandatory flags)"
	@echo "  lint-strict  flake8 + mypy --strict"
	@echo "  test         run the pytest suite"
	@echo "  visualize    run a generation with token-by-token trace"

install:
	uv sync

run:
	uv run python -m src

debug:
	uv run python -m pdb -m src

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf data/output/*.json

lint:
	uv run flake8 src/
	uv run mypy src/ --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs \
		--follow-imports=silent

lint-strict:
	uv run flake8 src/
	uv run mypy src/ --strict --follow-imports=silent

test:
	uv run pytest tests/ -v

visualize:
	uv run python -m src --visualize --input data/input/function_calling_tests.json
