# Makefile for the Pac-Man project.
PY := python3
CONFIG := config.json

.PHONY: install run debug lint lint-strict clean

install:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install pygame
	$(PY) -m pip install ./mazegenerator-*.whl

run:
	$(PY) pac-man.py $(CONFIG)

debug:
	$(PY) -m pdb pac-man.py $(CONFIG)

lint:
	flake8 --exclude=.venv,tests/* .
	mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs --exclude='^tests/'

clean:
	rm -rf __pycache__ */__pycache__ .mypy_cache .pytest_cache
