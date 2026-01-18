#!/usr/bin/env python3
"""
ex0.ft_command_quest
Learning how to use args
"""


def explore_command_line():
    """
    Function that manages users arguments and shows them
    """
    import sys

    print("=== Command Quest ===")
    print(f"Program name: {sys.argv[0]}")
    length = len(sys.argv)
    if length > 1:
        print(f"Arguments recieved: {length - 1}")
        for i, arg in enumerate(sys.argv[1:], 1):
            print(f"Argument {i}: {arg}")
    else:
        print("No arguments provided!")
    print(f"Total arguments: {length}")


explore_command_line()
