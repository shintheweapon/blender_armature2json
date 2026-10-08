# Runs the test suite inside Blender:
#   blender.exe -b -P tests/run_tests.py

import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)
SRC_DIR = os.path.join(REPO_DIR, 'src')
UNIT_DIR = os.path.join(TESTS_DIR, 'unit')


def main() -> int:
    """
    Discover and run every ``test_*.py`` module in the tests folder and in
    ``tests/unit``, the plain-Python tests that pytest also runs.

    Returns
    -------
    int
        0 when every test passes, otherwise 1.
    """
    # SRC_DIR lets the unit tests import core.* as they do under pytest
    for path in (REPO_DIR, TESTS_DIR, SRC_DIR):
        if path not in sys.path:
            sys.path.insert(0, path)
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite([
        loader.discover(TESTS_DIR, pattern='test_*.py'),
        # tests/unit has no __init__.py, so the first discover does not enter it
        loader.discover(UNIT_DIR, pattern='test_*.py', top_level_dir=UNIT_DIR),
    ])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
