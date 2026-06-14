# Fly-in - drone routing simulation
# Common automation tasks. Override MAP to run a different map, e.g.:
#     make run MAP=maps/fork.txt

PYTHON ?= python3
MAP    ?= maps/example.txt

MYPY_LINT_FLAGS = --warn-return-any --warn-unused-ignores \
	--ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

.PHONY: all install run debug clean lint lint-strict test help

all: lint

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) main.py $(MAP)

debug:
	$(PYTHON) -m pdb main.py $(MAP)

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache
	find . -name '*.pyc' -delete

lint:
	flake8 .
	mypy . $(MYPY_LINT_FLAGS)

lint-strict:
	flake8 .
	mypy . --strict

test:
	$(PYTHON) tests/validator.py maps/*.txt

help:
	@echo "Targets: install run debug clean lint lint-strict test"
	@echo "Override the map with: make run MAP=maps/fork.txt"
