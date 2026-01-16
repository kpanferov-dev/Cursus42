#!/usr/bin/env python3
"""
ft_different_errors.py
Program to test Standard errors
"""


def garden_operations():
    """Function that trigger standard errors"""

    print("Testing ValueError...")
    try:
        lst = [1,2]
        lst.index(4)
    except ValueError:
        print("Caught ValueError: invalid literal for int()\n")

    print("Testing ZeroDivisionError...")
    try:
        1/0
    except ZeroDivisionError:
        print("Caught ZeroDivisionError: division by zero\n")

    print("Testing FileNotFoundError...")
    try:
        open("missing.txt")
    except FileNotFoundError:
        print("Caught FileNotFoundError: No such file 'missing.txt'\n")

    print("Testing KeyError...")
    try:
        garden = {"owner": "Alice"}
        print(garden["missing\\_plant"])
    except KeyError:
        print("Caught KeyError: 'missing\\_plant'\n")

    print("Testing multiple errors together...")
    try:
        1/0
        int("abc")
    except (ZeroDivisionError, ValueError):
        print("Caught an error, but program continues!\n")


def test_error_types():
    """Function to test errors"""
    print("=== Garden Error Types Demo ===\n")
    garden_operations()
    print("All error types tested successfully!")


test_error_types()
