"""
Package manager for config
"""


__version__ = "1.0.0"

from .parser import parse_config_file
from .validator import validate_config
from .types import ConfigDict, ConfigValue
from .constants import (
    REQUIRED_KEYS,
    POSITIVE_INT,
    BOOL,
    TUPLES,
    ALGORITHMS,
    DISPLAYS,
    MAX_WIDTH,
    MAX_HEIGHT
)

__all__ = ["parse_config_file", "validate_config",
           "ConfigDict", "ConfigValue", "REQUIRED_KEYS",
           "POSITIVE_INT", "BOOL", "TUPLES", "ALGORITHMS",
           "DISPLAYS", "MAX_HEIGHT", "MAX_WIDTH"]
