"""Core implementation for directory-empty checks.

Design decisions, stated plainly:

1.  'Empty' means NO regular files exist at any depth. A directory that
    contains only empty subdirectories (recursively) is still considered
    empty. This is the single interpretation we picked; we do not also try
    to treat 'contains only subdirs' as non-empty, because supporting both
    readings in one flag has bitten other small libraries.

2.  We follow symlinks to directories but we do NOT recurse into them
    infinitely because we detect a symlink cycle via a visited-set keyed on
    (dev, inode). We do NOT follow broken symlinks; a broken symlink is not
    a regular file, so it does not make a directory 'non-empty' under our
    definition. This is a deliberate choice and is documented in the README.

3.  We raise our own NotADirectoryError (subclass of OSError) rather than
    letting the caller guess at exception types. FileNotFoundError is
    re-raised as NotADirectoryError for a uniform surface.

4.  We use os.scandir rather than os.walk because os.walk pre-materialises
    lists and makes early-exit awkward; scandir lets us stop the instant we
    find a single regular file.
"""

from __future__ import annotations

import os
from pathlib import Path


class DirectoryError(OSError):
    """Base class for errors raised by directory_empty_checker."""


class NotADirectoryError(DirectoryError):
    """Raised when the given path does not exist or is not a directory."""


def _realpath_key(entry_path: str):
    """Return a (st_dev, st_ino) key for a path, or None if unavailable.

    We use this to detect symlink cycles. os.stat follows symlinks, so two
    symlink entries that point at the same real directory will yield the
    same key. None means 'could not stat' — we treat that as 'not a cycle'
    rather than raising, because the caller may be on a filesystem where
    inodes aren't meaningful (e.g. some FAT mounts). The cost of a rare
    missed cycle is at most a long walk; the cost of a false cycle is a
    wrong answer.
    """
    try:
        st = os.stat(entry_path)
    except OSError:
        return None
    return (st.st_dev, st.st_ino)


def _directory_contains_file(dir_path: str, visited: set) -> bool:
    """Return True if dir_path (or any descendant) contains a regular file.

    'visited' is a set of (dev, ino) keys for directories we are currently
    recursing into, used to break symlink cycles. We add to it on entry and
    remove on exit so that legitimately-shared (via hardlinks — rare for
    dirs but legal on some systems) paths don't trigger false cycles.
    """
    key = _realpath_key(dir_path)
    if key is not None:
        if key in visited:
            return False
        visited.add(key)

    try:
        try:
            entries = os.scandir(dir_path)
        except NotADirectoryError:
            # os.scandir raises NotADirectoryError (builtin) when the path
            # exists but is a file. That should never reach here because the
            # caller checks, but be defensive: a file is not an empty dir.
            return True
        with entries:
            for entry in entries:
                # entry.is_file(follow_symlinks=True) returns True for
                # regular files and for symlinks that resolve to regular
                # files. That matches our definition of 'content'.
                if entry.is_file(follow_symlinks=True):
                    return True
                # A directory, or a symlink to a directory. Recurse.
                # is_dir follows symlinks by default.
                if entry.is_dir(follow_symlinks=True):
                    if _directory_contains_file(entry.path, visited):
                        return True
        return False
    finally:
        if key is not None:
            visited.discard(key)


def is_empty(path) -> bool:
    """Return True if `path` is a directory containing no regular files at
    any depth.

    A directory that contains only empty subdirectories (recursively) is
    considered empty. Symlinks to directories are followed; symlink cycles
    are detected and broken. Broken symlinks do not count as files.

    Args:
        path: A str, bytes, or os.PathLike pointing at a directory.

    Returns:
        bool: True if no regular file exists at or beneath `path`.

    Raises:
        NotADirectoryError: if `path` does not exist or is not a directory.
        DirectoryError: if the filesystem refuses to enumerate the
            directory tree.
    """
    # Normalise to a string path. We accept str/bytes/PathLike uniformly.
    # We deliberately do NOT call os.path.realpath here, because resolving
    # the root would collapse the caller's chosen path semantics; we only
    # resolve for cycle-detection inside the recursion.
    p = os.fspath(path)

    # Use lstat semantics to distinguish 'does not exist' from 'is a file'.
    # os.path.isdir follows symlinks, which is what we want for the entry
    # check, but it returns False for both non-existent paths AND files,
    # so we separate the cases for a better error message.
    if not os.path.exists(p):
        raise NotADirectoryError(f"path does not exist: {p!r}")
    if not os.path.isdir(p):
        raise NotADirectoryError(f"path is not a directory: {p!r}")

    try:
        return not _directory_contains_file(p, set())
    except OSError as exc:
        # Wrap unexpected OS errors in our base class so callers can catch
        # a single type. NotADirectoryError is already a DirectoryError.
        raise DirectoryError(str(exc)) from exc
