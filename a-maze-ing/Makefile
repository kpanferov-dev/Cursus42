PYTHON = python3
MAIN_FILE = a_maze_ing.py
CONFIG = config.txt

# Esto evita conflictos si por casualidad tienes una carpeta que se llame "clean" o "run"
.PHONY: install run debug clean lint lint-strict

install:
	pip install -r requirements.txt

run:
	$(PYTHON) $(MAIN_FILE) $(CONFIG)

debug:
	$(PYTHON) -m pdb $(MAIN_FILE)

clean:
	rm -rf __pycache__
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +

lint:
	python3 -m flake8
	python3 -m mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	python3 -m flake8
	python3 -m mypy . --strict