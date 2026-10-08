# Tests for src.core.hierarchy that need Blender; link_indices is tested in
# tests/unit/test_links.py

import unittest

import helpers
from src.core import hierarchy


class DepthFirstTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_parents_first_and_children_in_blender_order(self):
        arm = helpers.make_armature([
            ('Root', None, (0, 0, 0), (0, 0, 1), 0.0),
            ('A', 'Root', (0, 0, 1), (0, 0, 2), 0.0),
            ('B', 'Root', (1, 0, 1), (1, 0, 2), 0.0),
            ('A1', 'A', (0, 0, 2), (0, 0, 3), 0.0),
            ('Loose', None, (3, 0, 0), (3, 0, 1), 0.0),
        ])
        names = [b.name for b in hierarchy.depth_first_bones(arm.data)]
        blender_children = [c.name for c in arm.data.bones['Root'].children]
        a, b = blender_children
        expected = ['Root', a] + (['A1'] if a == 'A' else []) + [b] + \
                   (['A1'] if b == 'A' else []) + ['Loose']
        self.assertEqual(names, expected)
        for bone in hierarchy.depth_first_bones(arm.data):
            if bone.parent:
                self.assertLess(names.index(bone.parent.name), names.index(bone.name))


if __name__ == '__main__':
    unittest.main()
