# Tests for the sample check's choice of reference JSON: the path after --,
# or the .blend's own name with .json

import os
import unittest

from check_samples import reference_path

BLEND = os.path.join('samples', 'sample.blend')


class ReferencePathTests(unittest.TestCase):

    def test_path_after_double_dash(self):
        argv = ['blender.exe', '-b', BLEND, '-P', 'check_samples.py', '--', 'reference.json']
        self.assertEqual(reference_path(BLEND, argv), os.path.abspath('reference.json'))

    def test_blend_name_without_arguments(self):
        argv = ['blender.exe', '-b', BLEND, '-P', 'check_samples.py']
        self.assertEqual(reference_path(BLEND, argv), os.path.join('samples', 'sample.json'))

    def test_blend_name_with_nothing_after_double_dash(self):
        argv = ['blender.exe', '-b', BLEND, '-P', 'check_samples.py', '--']
        self.assertEqual(reference_path(BLEND, argv), os.path.join('samples', 'sample.json'))


if __name__ == '__main__':
    unittest.main()
