PY ?= uv run python
PKG := student

.PHONY: install run debug clean lint lint-strict test

install:
	uv venv
	uv sync --extra dev

run:
	$(PY) -m $(PKG) -- --help

debug:
	$(PY) -m pdb -m $(PKG) search "How to configure the OpenAI server?" --k 5

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache build dist
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest -q
