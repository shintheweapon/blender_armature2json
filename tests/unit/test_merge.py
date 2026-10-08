# Tests for core.merge (order, parents, reparent choices, input checks);
# plain Python, no Blender needed

import unittest

from core import merge


def node(name, parent=-1, flags=8):
    """Build a minimal valid input node."""
    zero = {'X': 0, 'Y': 0, 'Z': 0}
    return {'Name': name, 'ParentIndex': parent, 'FirstChildIndex': -1,
            'NextSiblingIndex': -1, 'PreviousSiblingIndex': -1,
            'Translation': dict(zero), 'Rotation': dict(zero),
            'Scale': {'X': 1, 'Y': 1, 'Z': 1},
            'BoundingBoxMin': dict(zero), 'BoundingBoxMax': dict(zero),
            'Flags': flags}


# Input: Root > Spine > Head bones, then a mesh node and a dummy owner
INPUT = [node('Root'), node('Spine', 0), node('Head', 1),
         node('Mesh', -1, flags=4), node('Owner', 0, flags=2)]
BONES = [('Root', None), ('Spine', 'Root'), ('Head', 'Spine')]


class OrderTests(unittest.TestCase):

    def test_nothing_added_keeps_order_and_parents(self):
        plan = merge.plan_merge(INPUT, BONES)
        self.assertEqual(plan.names, ['Root', 'Spine', 'Head', 'Mesh', 'Owner'])
        self.assertEqual(plan.parents, [-1, 0, 1, -1, 0])
        self.assertEqual(plan.added, [])
        self.assertEqual(plan.insertion, 3)

    def test_added_bones_go_after_last_bone_node_in_given_order(self):
        bones = BONES + [('Cloth1', 'Spine'), ('Cloth2', 'Cloth1')]
        plan = merge.plan_merge(INPUT, bones)
        self.assertEqual(plan.names,
                         ['Root', 'Spine', 'Head', 'Cloth1', 'Cloth2', 'Mesh', 'Owner'])
        self.assertEqual(plan.sources[3], ('added', 'Cloth1'))
        self.assertEqual(plan.parents, [-1, 0, 1, 1, 3, -1, 0])
        self.assertEqual(plan.insertion, 3)

    def test_flags_10_counts_as_bone_node(self):
        nodes = [node('Root'), node('Mesh', -1, flags=4), node('Both', 0, flags=10),
                 node('Owner', 0, flags=2)]
        plan = merge.plan_merge(nodes, [('Root', None), ('New', 'Root')])
        self.assertEqual(plan.insertion, 3)
        self.assertEqual(plan.names[3], 'New')

    def test_no_bone_node_inserts_at_zero(self):
        nodes = [node('Mesh', -1, flags=4)]
        plan = merge.plan_merge(nodes, [('New', None)])
        self.assertEqual(plan.names, ['New', 'Mesh'])
        self.assertEqual(plan.insertion, 0)

    def test_links_follow_output_parents(self):
        plan = merge.plan_merge(INPUT, BONES + [('Cloth1', 'Spine')])
        # Spine's children: Head (2) then Cloth1 (3)
        self.assertEqual(plan.links[1]['FirstChildIndex'], 2)
        self.assertEqual(plan.links[2]['NextSiblingIndex'], 3)
        self.assertEqual(plan.links[3]['PreviousSiblingIndex'], 2)


class InputOnlyTests(unittest.TestCase):

    def test_input_only_nodes_kept_and_parent_repointed_after_shift(self):
        plan = merge.plan_merge(INPUT, BONES + [('Cloth1', 'Spine')])
        # Owner's parent Root stays index 0; Owner itself moved from 4 to 5
        self.assertEqual(plan.names[5], 'Owner')
        self.assertEqual(plan.parents[5], 0)
        self.assertEqual(plan.input_only, ['Mesh', 'Owner'])

    def test_input_only_parent_after_insertion_is_repointed(self):
        nodes = INPUT + [node('Child', 3, flags=2)]
        plan = merge.plan_merge(nodes, BONES + [('Cloth1', 'Spine')])
        self.assertEqual(plan.names[plan.parents[6]], 'Mesh')
        self.assertEqual(plan.parents[6], 4)


class ReparentTests(unittest.TestCase):
    # In Blender, Head is moved under Root

    bones = [('Root', None), ('Spine', 'Root'), ('Head', 'Root')]

    def test_keep_input_parent_by_default_and_reported(self):
        plan = merge.plan_merge(INPUT, self.bones)
        self.assertEqual(plan.parents[2], 1)
        self.assertEqual(plan.reparented, ['Head'])
        self.assertEqual(plan.recompute, [])

    def test_blender_keep_placement_recomputes(self):
        plan = merge.plan_merge(INPUT, self.bones, merge.BLENDER_KEEP_PLACEMENT)
        self.assertEqual(plan.parents[2], 0)
        self.assertEqual(plan.recompute, [2])

    def test_blender_as_is_does_not_recompute(self):
        plan = merge.plan_merge(INPUT, self.bones, merge.BLENDER_AS_IS)
        self.assertEqual(plan.parents[2], 0)
        self.assertEqual(plan.recompute, [])
        self.assertEqual(plan.reparented, ['Head'])

    def test_reparent_under_added_bone_refused(self):
        bones = [('Root', None), ('Spine', 'Root'), ('Helper', 'Spine'), ('Head', 'Helper')]
        with self.assertRaisesRegex(ValueError, "'Head' would come before its parent 'Helper'"):
            merge.plan_merge(INPUT, bones, merge.BLENDER_KEEP_PLACEMENT)
        # Keeping the input parent is fine
        plan = merge.plan_merge(INPUT, bones)
        self.assertEqual(plan.reparented, ['Head'])

    def test_unknown_choice_refused(self):
        with self.assertRaises(ValueError):
            merge.plan_merge(INPUT, BONES, 'SOMETHING')


class ValidateInputTests(unittest.TestCase):

    def test_valid_input_passes(self):
        merge.validate_input(INPUT)

    def test_not_a_list(self):
        with self.assertRaisesRegex(ValueError, 'must be a list'):
            merge.validate_input({'Name': 'Root'})

    def test_node_not_an_object(self):
        with self.assertRaisesRegex(ValueError, 'not an object'):
            merge.validate_input([node('Root'), 'Spine'])

    def test_missing_field(self):
        broken = node('Root')
        del broken['Flags']
        with self.assertRaisesRegex(ValueError, 'lacks Flags'):
            merge.validate_input([broken])

    def test_missing_name(self):
        with self.assertRaisesRegex(ValueError, 'has no name'):
            merge.validate_input([node('')])

    def test_duplicate_names(self):
        with self.assertRaisesRegex(ValueError, "two nodes named 'Root'"):
            merge.validate_input([node('Root'), node('Root', 0)])

    def test_parent_out_of_range_or_self(self):
        with self.assertRaisesRegex(ValueError, 'points at no other node'):
            merge.validate_input([node('Root', 5)])
        with self.assertRaisesRegex(ValueError, 'points at no other node'):
            merge.validate_input([node('Root', 0)])


if __name__ == '__main__':
    unittest.main()
