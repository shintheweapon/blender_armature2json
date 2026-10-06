# Runs the test suite inside Blender:
#   blender.exe -b -P tests/run_tests.py

import os
import sys
import unittest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(TESTS_DIR)


def main() -> int:
    """
    Discover and run every ``test_*.py`` module in the tests folder.

    Returns
    -------
    int
        0 when every test passes, otherwise 1.
    """
    for path in (REPO_DIR, TESTS_DIR):
        if path not in sys.path:
            sys.path.insert(0, path)
    suite = unittest.defaultTestLoader.discover(TESTS_DIR, pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
