"""
Package manager
"""


__version__ = "1.0.0"

from .ascii import AsciiRender
from .graphic import PygameRender

__all__ = ["AsciiRender", "PygameRender"]
