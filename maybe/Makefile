# call me maybe - constrained-decoding function calling
# The reviewer/moulinette runs `uv sync`; these targets wrap common tasks.

FUNCTIONS ?= data/input/functions_definition.json
INPUT     ?= data/input/function_calling_tests.json
OUTPUT    ?= data/output/function_calling_results.json

MYPY_LINT_FLAGS = --warn-return-any --warn-unused-ignores \
	--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

.PHONY: all install run debug clean lint lint-strict test help

all: lint test

install:
	uv sync

run:
	uv run python -m src --functions_definition $(FUNCTIONS) \
		--input $(INPUT) --output $(OUTPUT)

debug:
	uv run python -m pdb -m src --functions_definition $(FUNCTIONS) \
		--input $(INPUT) --output $(OUTPUT)

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache
	find . -name '*.pyc' -delete

lint:
	uv run flake8 .
	uv run mypy . $(MYPY_LINT_FLAGS)

lint-strict:
	uv run flake8 .
	uv run mypy . --strict

test:
	uv run pytest -q

help:
	@echo "Targets: install run debug clean lint lint-strict test"
