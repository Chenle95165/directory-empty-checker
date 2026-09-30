"""Directory Empty Checker.

A small, zero-dependency library that reports whether a directory is empty,
where 'empty' means: no regular files anywhere beneath it, and no
subdirectory that itself contains a regular file (recursively).

Exported names:
    is_empty(path)      -> bool
    DirectoryError      -> Exception base class for errors raised here
    NotADirectoryError  -> raised when path is not a directory
    Path                 -> re-exported pathlib.Path for convenience
"""

from .core import (
    DirectoryError,
    NotADirectoryError,
    is_empty,
)
from pathlib import Path

__all__ = [
    "DirectoryError",
    "NotADirectoryError",
    "Path",
    "is_empty",
]
