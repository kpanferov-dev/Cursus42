#!/usr/bin/env python3

from typing import Tuple, cast
from config.parser import parse_config_file
from config.validator import validate_config
from mazegen.maze import Maze
from mazegen.maze_generator import MazeGenerator
from render import AsciiRender, PygameRender
import sys


def main() -> None:
    print("A-Maze-Ing\n")
    try:
        if not (len(sys.argv) > 1):
            print("Invalid arguments, example -> "
                  "python3 a_maze_ing.py config.txt")
            return
        config = parse_config_file(sys.argv[1])
        validate_config(config)

        print("-------Config-------")
        print(config)
        print()
        width = cast(int, config["width"])
        height = cast(int, config["height"])
        entry = cast(Tuple[int, int], config["entry"])
        exit = cast(Tuple[int, int], config["exit"])
        algorithm = cast(str, config["algorithm"])
        seed = cast(int, config["seed"])
        output_file: str = cast(str, config["output_file"])
        display: str = cast(str, config["display"])
        perfect: bool = cast(bool, config["perfect"])

        maze = Maze(
            width=width,
            height=height,
            entry=entry,
            exit=exit,
            perfect=perfect
        )
        generator = MazeGenerator(seed)
        try:
            generator.set_logo_42(maze)
        except Exception:
            print("The entry or the exit are on an invalid position")
            return
        generator.generate_maze(maze, algorithm)

        if display == "ascii":
            AsciiRender(output_file).run(
                maze,
                generator=generator,
                algorithm=algorithm,
                apply_logo_42=True,
                seed=seed,
            )
        else:
            PygameRender(cell_size=32,
                         output_file=output_file).draw_maze(
                maze,
                generator=generator,
                algorithm=algorithm,
                apply_logo_42=True,
                seed=seed,
            )
    except (ValueError, FileNotFoundError) as e:
        print(e)


if __name__ == "__main__":
    main()
