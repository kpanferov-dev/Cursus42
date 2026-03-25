"""
types
Contains types used by render
"""

from typing import Union, Tuple, Dict


ConfigValue = Union[int, bool, Tuple[int, int], Tuple[int, ...], str]
ConfigDict = Dict[str, ConfigValue]
