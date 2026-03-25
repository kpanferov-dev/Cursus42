"""
validator.py
Contains functions to validate config file content.
"""

from typing import Tuple, cast
from .types import ConfigDict
from .constants import (
    REQUIRED_KEYS,
    POSITIVE_INT,
    BOOL,
    TUPLES,
    ALGORITHMS,
    DISPLAYS,
    MAX_HEIGHT,
    MAX_WIDTH
)


def validate_positive_int(config: ConfigDict, key: str) -> None:
    """
    Validate that a config key contains a positive integer.

    Args:
        config (ConfigDict): The configuration dictionary.
        key (str): The key to validate in the config.

    Raises:
        ValueError: If the value is not an integer or is negative.
    """
    value = config[key]

    if not isinstance(value, int) or value < 0:
        raise ValueError(f"{key.capitalize()} must be a positive integer")


def validate_bool(config: ConfigDict, key: str) -> None:
    """
    Validate that a config key contains a boolean value.

    Args:
        config (ConfigDict): The configuration dictionary.
        key (str): The key to validate in the config.

    Raises:
        ValueError: If the value is not a boolean.
    """
    value = config[key]

    if not isinstance(value, bool):
        raise ValueError(f"{key.capitalize()} must be a boolean")


def validate_tuples(config: ConfigDict, key: str) -> None:
    """
    Validate that a config key contains a tuple of two positive integers.

    Args:
        config (ConfigDict): The configuration dictionary.
        key (str): The key to validate in the config.

    Raises:
        ValueError: If the value is not a tuple of length 2,
        or any element is not a positive integer.
    """
    value = config[key]

    if not (isinstance(value, tuple) and len(value) == 2):
        raise ValueError(f"{key.capitalize()} must be a tuple of 2 integers")

    for elem in value:
        if not isinstance(elem, int) or elem < 0:
            raise ValueError(f"Elements of {key} must be positive integers")


def validate_str(config: ConfigDict, key: str, allowed: set[str]) -> None:
    """
    Validate that a config key contains a
    string within a set of allowed values.

    Args:
        config (ConfigDict): The configuration dictionary.
        key (str): The key to validate in the config.
        allowed (set[str]): A set of allowed string values for this key.

    Raises:
        ValueError: If the value is not a string or not in the allowed set.
    """
    value = config[key]

    if not isinstance(value, str):
        raise ValueError(f"{key.capitalize()} must be a string")

    if value not in allowed:
        raise ValueError(f"Invalid {key}: {value}. Allowed values: {allowed}")


def validate_file(config: ConfigDict, key: str) -> None:
    """
    Validate that a config key contains a string ending with '.txt'.

    Args:
        config (ConfigDict): The configuration dictionary.
        key (str): The key to validate in the config.

    Raises:
        ValueError: If the value is not a string or does not end with '.txt'.
    """
    value = config[key]

    if not isinstance(value, str):
        raise ValueError(f"{key.capitalize()} must be a string")

    if not value.endswith(".txt"):
        raise ValueError(f"{key.capitalize()} must end with .txt")


def validate_basic_config(config: ConfigDict) -> None:
    """
    Validate the basic configuration: types,
    required keys, values of type int, bool, tuples, etc.

    Args:
        config (ConfigDict): The configuration dictionary to validate.

    Raises:
        ValueError: If any basic validation
        fails (missing keys or invalid values).
    """
    missing_keys = REQUIRED_KEYS - set(config.keys())
    if missing_keys:
        raise ValueError(f"Missing config keys: {missing_keys}")

    for key in POSITIVE_INT:
        validate_positive_int(config, key)

    for key in BOOL:
        validate_bool(config, key)

    for key in TUPLES:
        validate_tuples(config, key)

    validate_str(config, "algorithm", ALGORITHMS)
    validate_str(config, "display", DISPLAYS)

    validate_file(config, "output_file")


def validate_business_rules(config: ConfigDict) -> None:
    """
    Validate business-specific rules for the configuration.

    This function ensures that:
    - The `width` does not exceed the maximum allowed (`MAX_WIDTH`).
    - The `height` does not exceed the maximum allowed (`MAX_HEIGHT`).
    - The `entry` and `exit` positions are different.
    - The `entry` and `exit` positions are within the
    bounds defined by `width` and `height`.

    Args:
        config (ConfigDict): The configuration dictionary to
        validate. It must contain the keys:
            - 'width': An integer representing the width of the maze.
            - 'height': An integer representing the height of the maze.
            - 'entry': A tuple (x, y) representing the
            entry position in the maze.
            - 'exit': A tuple (x, y) representing the
            exit position in the maze.

    Raises:
        ValueError: If any of the business rules are violated:
            - If `width` exceeds `MAX_WIDTH`.
            - If `height` exceeds `MAX_HEIGHT`.
            - If `entry` is the same as `exit`.
            - If `entry` or `exit` are out of bounds
            based on `width` and `height`.
    """
    width: int = cast(int, config.get("width"))
    height: int = cast(int, config.get("height"))
    entry: tuple[int, int] = cast(Tuple[int, int], config["entry"])
    exit: tuple[int, int] = cast(Tuple[int, int], config["exit"])

    if width > MAX_WIDTH:
        raise ValueError("Width must be no greater " +
                         f"than {MAX_WIDTH}. Current value: {width}")

    if height > MAX_HEIGHT:
        raise ValueError("Height must be no greater " +
                         f"than {MAX_HEIGHT}. Current value: {height}")

    if entry == exit:
        raise ValueError("Entry must be different from exit")

    if not (0 <= entry[0] < width and 0 <= entry[1] < height):
        raise ValueError(f"Entry {entry} is out of bounds.")

    if not (0 <= exit[0] < width and 0 <= exit[1] < height):
        raise ValueError(f"Exit {exit} is out of bounds.")


def validate_config(config: ConfigDict) -> None:
    """
    Validate the entire configuration by performing both basic validations
    (such as type checks and required keys) and business-specific rules.

    This function first calls `validate_basic_config`
    to ensure the configuration
    contains valid types and all required keys, and then checks the business
    logic with `validate_business_rules`.

    Args:
        config (ConfigDict): The configuration dictionary to validate.

    Raises:
        ValueError: If any validation fails
        (either basic validation or business rules).
    """
    validate_basic_config(config)
    validate_business_rules(config)
