# Directory Empty Checker

Reports whether a directory contains no regular files at any depth. A directory that holds only empty subdirectories (recursively) is considered empty.

```python
from directory_empty_checker import is_empty

import os, tempfile
d = tempfile.mkdtemp()
print(is_empty(d))  # -> True
```

## Why this exists

You have a cleanup step that should only run when a directory has been fully drained of files — but the directory may contain nested folder structures you don't want to flatten just to ask "is anything in here?". Walking the tree by hand each time is tedious and easy to get wrong (symlink cycles, broken links, off-by-one recursion).

This library makes one decision and sticks to it: **empty means no regular files anywhere beneath the path, period.** Subdirectories alone don't count. There is no `include_dirs` flag, no `follow_symlinks` knob. If you need a different definition, this is the wrong library and that's fine.

## The awkward edge

Symlinks. The library follows symlinks to directories (so a symlink to a non-empty directory makes the parent non-empty) and detects cycles via `(dev, inode)` keys so `a -> b -> a` doesn't hang. **Broken symlinks do not count as files** — they're not regular files, so an otherwise-empty dir containing a dangling link reports `True`. If you need broken links to count as "content", handle that before calling.

## API

- `is_empty(path) -> bool` — `True` if `path` is a directory containing no regular files at any depth.
- `NotADirectoryError` — raised by `is_empty` when `path` doesn't exist or isn't a directory. Subclass of `DirectoryError`.
- `DirectoryError` — base error class, subclass of `OSError`.
- `Path` — re-exported `pathlib.Path` for convenience.

## Running the tests

```
PYTHONPATH=src python -m unittest discover -s tests
```

Zero third-party dependencies. Standard library only.

## Design notes

The window stores values eagerly rather than keeping running aggregates. Running
sums drift with floating point over long streams, and recomputing from a small
buffer is cheap enough that the drift is not worth the speed.

