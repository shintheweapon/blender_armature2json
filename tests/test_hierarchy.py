# Tests for src.core.hierarchy

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


class LinkIndicesTests(unittest.TestCase):

    def test_links_for_branching_tree_with_two_roots(self):
        #   0 Root ── 1 A ── 2 A1
        #          └─ 3 B
        #   4 Loose (second root)
        links = hierarchy.link_indices([-1, 0, 1, 0, -1])
        expected = [
            {'FirstChildIndex': 1, 'NextSiblingIndex': 4, 'PreviousSiblingIndex': -1},
            {'FirstChildIndex': 2, 'NextSiblingIndex': 3, 'PreviousSiblingIndex': -1},
            {'FirstChildIndex': -1, 'NextSiblingIndex': -1, 'PreviousSiblingIndex': -1},
            {'FirstChildIndex': -1, 'NextSiblingIndex': -1, 'PreviousSiblingIndex': 1},
            {'FirstChildIndex': -1, 'NextSiblingIndex': -1, 'PreviousSiblingIndex': 0},
        ]
        self.assertEqual(links, expected)

    def test_parent_after_child_raises(self):
        with self.assertRaises(ValueError):
            hierarchy.link_indices([-1, 2, 0])


if __name__ == '__main__':
    unittest.main()
