"""
Root __init__.py - Makes the entire repository a Python package
This allows importing from ex0, ... , ex4 as subpackages
"""

from . import ex0
from . import ex1
from . import ex2
from . import ex3

__all__ = ['ex0', 'ex1', 'ex2', 'ex3']
