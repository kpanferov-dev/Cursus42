*This project has been created as part of the 42 curriculum by marcsan2, kpanfero*

# A-Maze-Ing
--------------------------------------------------------------------------------
# Description:
This project is a maze generator developed in Python 3.10+. It takes a configuration file to generate a perfect maze (with a single path between the entry and exit) and writes it to a file using a hexadecimal representation for its walls. Additionally, it includes a visual representation (either terminal ASCII rendering or a graphical display) that clearly shows the walls, entry, exit, the shortest solution path, and a "42" pattern drawn by fully closed cells
You can chose wich one of the three algorithms you can use for generating the maze.

# Instructions (Installation & Usage)
The project includes a Makefile to automate common tasks. You can use the following rules:
make install: Installs project dependencies using a package manager of your choice (pip, uv, etc.).
make run: Executes the main script of the project.
make debug: Runs the main script in debug mode using Python's built-in debugger (e.g., pdb).
make lint: Executes flake8 and mypy with the required flags to check typing and coding standards.
make clean: Removes temporary files or caches (e.g., __pycache__, .mypy_cache).

# Execution
python3 a_maze_ing.py config.txt

## Interactive commands:

r: Regenerate maze
p: Show/hide shortest path
a: Toggle path animation
c: Change wall color
l: Toggle 42 logo color
color: Toggle ANSI colors
q: Quit

# Pygame Renderer

## Keyboard controls:

R: Regenerate maze
P: Show/hide shortest path
C: Change wall color
L: Toggle 42 logo coloring
ESC: Exit

## Keyboard controls:

R: Regenerate maze
P: Show/hide shortest path
C: Change wall color
L: Toggle 42 logo coloring
ESC: Exit

# AI Usage
AI (ChatGPT) was used to:
Review code and improve docstrings
Learning comprehension
General questions and suggestions

# Configuration File

The project saves maze solutions in a text file in the following format:

<maze grid in hex representation>
<entry_x>,<entry_y>
<exit_x>,<exit_y>
<directions string for shortest path>

# Algorithm Choice

The default generation algorithm is DFS / Backtracking, because:

It is simple and easy to implement
Produces perfect mazes with long winding paths
Works efficiently for interactive visualization

Optional algorithms (Prim, Kruskal) are available via configuration or command-line selection.

# Reusability
mazegen folder is reusable: all maze generation logic.

pip install build
python -m build
pip install dist/mazegen-1.0.0-py3-none-any.whl

To test if its installed just need to remove the folder which has been put into 
the package and make run

# Team and Project Management

## Roles:
marcsan2: Core maze generation, ASCII renderer, solver, README
kpanfero: Pygame renderer, UI/UX design, testing, documentation, project management


## Planning:
Initial design: DFS maze generation
Added extra algorithms (Prim/Kruskal) for flexibility
Implemented interactive renderers sequentially
Added logo overlay as a bonus feature
Tools used:
Python 3.10+
Pygame
Flake8 for linting
Git and GitHub for version control
AI assistant for code review and documentation
Retrospective:
What worked well: Modular design, interactive renderers
Improvements: More advanced path animation and editor features could be added

## Advanced Features
Multiple algorithms selectable at runtime
Interactive visualizations with color palettes
Optional animated shortest path display
Logo overlay integrated into maze generation

# Project Structure

```text
project/
├── mazegen/
│   ├── maze_generator.py 
│   ├── core/
│   │   ├── __init__.py
│   │   ├── cell.py
│   │   ├── constants.py
│   │   ├── maze.py
│   │   └── solver.py       
├── render/
│   ├── __init__.py
│   ├── render.py             
│   ├── ascii.py
│   └── graphic.py
├── config/
│   ├── __init__.py
│   ├── constants.py
│   ├── parser.py
│   ├── types.py
│   └── validator.py
├── a_maze_ing.py
├── pyproject.toml
├── config.txt
├── .gitignore
├── README.md
├── requirements.txt
└── makefile

## Wall Combinations Table LSB

| Binary  | Decimal | Hexadecimal |    Closed Walls    |
| ------- | ------- | ----------- | ------------------ |
| 0000    | 0       | 0x0         | Ninguno            |
| 0001    | 1       | 0x1         | N                  |
| 0010    | 2       | 0x2         | E                  |
| 0011    | 3       | 0x3         | E, N               |
| 0100    | 4       | 0x4         | S                  |
| 0101    | 5       | 0x5         | S, N               |
| 0110    | 6       | 0x6         | S, E               |
| 0111    | 7       | 0x7         | S, E, N            |
| 1000    | 8       | 0x8         | W                  |
| 1001    | 9       | 0x9         | W, N               |
| 1010    | 10      | 0xA         | W, E               |
| 1011    | 11      | 0xB         | W, E, N            |
| 1100    | 12      | 0xC         | W, S               |
| 1101    | 13      | 0xD         | W, S, N            |
| 1110    | 14      | 0xE         | W, S, E            |
| 1111    | 15      | 0xF         | -All- (W, S, E, N) |
