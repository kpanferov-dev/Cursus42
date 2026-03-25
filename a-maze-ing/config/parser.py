"""
parser.py
Contains functions to parse config.txt and convert values.
"""

from .types import ConfigValue, ConfigDict


def convert_value(value: str) -> ConfigValue:
    """
    Convert a string from the config file into an appropriate Python type.

    The function tries to interpret the string as
    one of the following types, in order:
    - Boolean: "true" or "false" (case insensitive)
    - Tuple of integers: comma-separated values like "0,0"
    - Integer
    - String: if no other conversion applies

    Args:
        value (str): The string value from the config file.

    Returns:
        ConfigValue: The converted value as int, bool, tuple[int, int], or str.
    """
    value = value.strip()

    if value.lower() == "true":
        return True
    elif value.lower() == "false":
        return False
    elif "," in value:
        try:
            return tuple(int(x.strip()) for x in value.split(","))
        except ValueError:
            pass

    try:
        return int(value)
    except ValueError:
        pass

    return value


def parse_config_file(path: str) -> ConfigDict:
    """
    Read a key=value configuration file and convert its values.

    Each line of the file should be in the format:
        KEY=VALUE
    - Keys are converted to lowercase.
    - Values are converted to int, bool,
    tuple[int, int], or str using `convert_value`.

    Lines starting with '#' or empty lines are ignored.

    Args:
        path (str): The path to the configuration file.

    Returns:
        ConfigDict: A dictionary mapping keys
        (str) to converted values (ConfigValue).

    Raises:
        ValueError: If a line does not contain an '=' separator.
    """
    config = {}

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if "=" not in line:
                raise ValueError(f"Invalid line: {line}")

            key, value = line.split("=", 1)
            config[key.strip().lower()] = convert_value(value)

    return config
