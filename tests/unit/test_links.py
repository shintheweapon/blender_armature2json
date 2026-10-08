# Tests for core.hierarchy.link_indices; plain Python, no Blender needed

import unittest

from core import hierarchy


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

    def test_siblings_follow_list_order_not_insertion_into_parent(self):
        # Children of 0 at 1, 3 and 4: siblings chain in index order
        links = hierarchy.link_indices([-1, 0, 1, 0, 0])
        self.assertEqual(links[0]['FirstChildIndex'], 1)
        self.assertEqual([links[i]['NextSiblingIndex'] for i in (1, 3, 4)], [3, 4, -1])
        self.assertEqual([links[i]['PreviousSiblingIndex'] for i in (1, 3, 4)], [-1, 1, 3])

    def test_parent_after_child_raises(self):
        with self.assertRaises(ValueError):
            hierarchy.link_indices([-1, 2, 0])

    def test_parent_pointing_at_itself_raises(self):
        with self.assertRaises(ValueError):
            hierarchy.link_indices([-1, 1])


if __name__ == '__main__':
    unittest.main()
