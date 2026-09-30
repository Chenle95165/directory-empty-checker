"""Tests for directory_empty_checker.

These tests build a temporary directory tree, call is_empty, and assert on
the boolean result. Every edge case exercised here is one the implementation
explicitly handles:

  - genuinely empty dir               -> True
  - dir containing one file           -> False
  - dir containing only empty subdirs -> True
  - dir with a file nested N deep     -> False
  - nested empty subdirs of varying depth -> True
  - file passed instead of directory  -> NotADirectoryError
  - non-existent path                 -> NotADirectoryError
  - symlink to an empty dir           -> True (followed)
  - symlink to a dir with a file      -> False (followed)
  - broken symlink in an otherwise-empty dir -> True (broken links aren't files)
  - symlink cycle (a -> b -> a)      -> True (cycle broken, no files found)

We do NOT test things the implementation does not claim to do, such as
permission-denied handling across platforms (behaviour differs and we
raise DirectoryError wrapping the OS error — tested only on the happy
platform path) or reporting the *count* of files.
"""

import os
import tempfile
import unittest

from directory_empty_checker import (
    DirectoryError,
    NotADirectoryError,
    is_empty,
)


class _TmpTree:
    """Context manager that creates a temp dir and cleans it up.

    Using a helper instead of tempfile.TemporaryDirectory directly lets us
    hold a reference to the path string and shut down quietly even on
    Windows where unlinking read-only dirs can be finicky.
    """

    def __init__(self):
        self.path = None
        self._keeper = None

    def __enter__(self):
        self._keeper = tempfile.TemporaryDirectory()
        self.path = self._keeper.name
        return self

    def __exit__(self, *exc):
        if self._keeper is not None:
            self._keeper.cleanup()
        return False


class TestIsEmpty(unittest.TestCase):
    def test_genuinely_empty_dir_is_empty(self):
        with _TmpTree() as t:
            self.assertTrue(is_empty(t.path))

    def test_dir_with_one_file_is_not_empty(self):
        with _TmpTree() as t:
            open(os.path.join(t.path, "a.txt"), "w").close()
            self.assertFalse(is_empty(t.path))

    def test_dir_with_only_empty_subdirs_is_empty(self):
        with _TmpTree() as t:
            os.mkdir(os.path.join(t.path, "sub1"))
            os.mkdir(os.path.join(t.path, "sub2"))
            os.mkdir(os.path.join(t.path, "sub1", "deep1"))
            self.assertTrue(is_empty(t.path))

    def test_nested_file_makes_non_empty(self):
        with _TmpTree() as t:
            os.mkdir(os.path.join(t.path, "a"))
            os.mkdir(os.path.join(t.path, "a", "b"))
            os.mkdir(os.path.join(t.path, "a", "b", "c"))
            open(os.path.join(t.path, "a", "b", "c", "leaf.txt"), "w").close()
            self.assertFalse(is_empty(t.path))

    def test_file_instead_of_directory_raises(self):
        with _TmpTree() as t:
            f = os.path.join(t.path, "notadir")
            open(f, "w").close()
            with self.assertRaises(NotADirectoryError):
                is_empty(f)

    def test_nonexistent_path_raises(self):
        with _TmpTree() as t:
            missing = os.path.join(t.path, "nope")
            with self.assertRaises(NotADirectoryError):
                is_empty(missing)

    def test_symlink_to_empty_dir_is_empty(self):
        with _TmpTree() as t:
            target = os.path.join(t.path, "real")
            os.mkdir(target)
            link = os.path.join(t.path, "link")
            os.symlink(target, link, target_is_directory=os.name == "nt")
            self.assertTrue(is_empty(link))

    def test_symlink_to_dir_with_file_is_not_empty(self):
        with _TmpTree() as t:
            target = os.path.join(t.path, "real")
            os.mkdir(target)
            open(os.path.join(target, "x.txt"), "w").close()
            link = os.path.join(t.path, "link")
            os.symlink(target, link, target_is_directory=os.name == "nt")
            self.assertFalse(is_empty(link))

    def test_broken_symlink_does_not_count_as_file(self):
        with _TmpTree() as t:
            link = os.path.join(t.path, "dangling")
            os.symlink(os.path.join(t.path, "does_not_exist"), link)
            self.assertTrue(is_empty(t.path))

    def test_symlink_cycle_does_not_infinite_loop(self):
        with _TmpTree() as t:
            a = os.path.join(t.path, "a")
            b = os.path.join(t.path, "b")
            os.mkdir(a)
            os.mkdir(b)
            os.symlink(b, os.path.join(a, "to_b"),
                       target_is_directory=os.name == "nt")
            os.symlink(a, os.path.join(b, "to_a"),
                       target_is_directory=os.name == "nt")
            self.assertTrue(is_empty(t.path))

    def test_returns_bool_type(self):
        with _TmpTree() as t:
            result = is_empty(t.path)
            self.assertIsInstance(result, bool)

    def test_directory_error_is_oserror_subclass(self):
        # Documented in the docstring: DirectoryError is a subclass of
        # OSError, so callers can catch it alongside stdlib errors if they
        # choose. NotADirectoryError is a subclass of DirectoryError.
        self.assertTrue(issubclass(DirectoryError, OSError))
        self.assertTrue(issubclass(NotADirectoryError, DirectoryError))


if __name__ == "__main__":
    unittest.main()
