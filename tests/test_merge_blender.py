# Tests for src.core.writer.merge_nodes, which needs Blender; the merge
# order and parent rules are tested in tests/unit/test_merge.py

import copy
import unittest

import bpy

import helpers
from src.core import merge, transforms, writer

BONES = [
    ('UpperArm', None, (0, 0, 0), (0, 1, 0), 0.0),
    ('Forearm', 'UpperArm', (0, 1, 0), (0, 2, 0.2), 0.3),
    ('Hand', 'Forearm', (0, 2, 0.2), (0, 2.5, 0.2), 0.0),
    ('Cloth', 'Forearm', (0.3, 1.5, 0), (0.3, 1.5, -0.6), 0.5),
]


def without(nodes, names):
    """Remove nodes by name and re-point the remaining parents by name."""
    kept = [copy.deepcopy(n) for n in nodes if n['Name'] not in names]
    index_of = {n['Name']: i for i, n in enumerate(kept)}
    for n in kept:
        parent = n['ParentIndex']
        n['ParentIndex'] = index_of[nodes[parent]['Name']] if parent >= 0 else -1
    return kept


def by_name(nodes):
    return {n['Name']: n for n in nodes}


class MergeNodesTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        self.arm = helpers.make_armature(BONES)
        helpers.make_skinned_box(self.arm, 'Cloth', (0.2, 0.3, 0.4))
        self.full = writer.build_nodes(self.arm, mark_root_as_mesh=False)

    def assertSamePosition(self, a, b, places=5):
        for k in range(3):
            self.assertAlmostEqual(a[k], b[k], places=places)

    def test_unchanged_input_comes_out_identical(self):
        nodes, plan = writer.merge_nodes(self.arm, copy.deepcopy(self.full))
        self.assertEqual(nodes, self.full)
        self.assertEqual(plan.added, [])
        self.assertEqual(plan.input_only, [])

    def test_removed_bones_come_back_in_place_with_boxes(self):
        partial = without(self.full, {'Hand', 'Cloth'})
        nodes, plan = writer.merge_nodes(self.arm, partial)
        self.assertEqual(plan.added, ['Hand', 'Cloth'])
        self.assertEqual([n['Name'] for n in nodes[:2]], ['UpperArm', 'Forearm'])
        out_worlds = transforms.world_matrices(nodes)
        ref_worlds = transforms.world_matrices(self.full)
        ref_index = {n['Name']: i for i, n in enumerate(self.full)}
        for i, n in enumerate(nodes):
            self.assertSamePosition(out_worlds[i].translation,
                                    ref_worlds[ref_index[n['Name']]].translation)
        cloth = by_name(nodes)['Cloth']
        reference = by_name(self.full)['Cloth']
        self.assertEqual(cloth['BoundingBoxMin'], reference['BoundingBoxMin'])
        self.assertEqual(cloth['BoundingBoxMax'], reference['BoundingBoxMax'])
        self.assertEqual(cloth['Flags'], 8)

    def test_added_child_lands_in_place_under_parent_with_other_axes(self):
        # The input's Forearm keeps the same position but other axes, as a
        # vanilla node can; the added Cloth must still land where its bone is
        partial = without(self.full, {'Cloth'})
        forearm = by_name(partial)['Forearm']
        forearm['Rotation'] = {'X': 0.7, 'Y': -0.4, 'Z': 1.1}
        nodes, _ = writer.merge_nodes(self.arm, partial)
        index = {n['Name']: i for i, n in enumerate(nodes)}
        out_world = transforms.world_matrices(nodes)[index['Cloth']]
        bone_world = transforms.node_matrix(transforms.space_mapping('BLENDER_WORLD',
                                                                     self.arm.matrix_world),
                                            self.arm.matrix_world,
                                            self.arm.data.bones['Cloth'].matrix_local,
                                            transforms.axis_matrix())
        self.assertSamePosition(out_world.translation, bone_world.translation)
        # Same axes as the bone too, so the box matches the plain export
        self.assertEqual(nodes[index['Cloth']]['BoundingBoxMax'],
                         by_name(self.full)['Cloth']['BoundingBoxMax'])

    def _reparented_input(self):
        # README example: the input has Hand under Forearm; in Blender, Hand
        # is moved under UpperArm
        partial = copy.deepcopy(self.full)
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = self.arm.data.edit_bones
        edit_bones['Hand'].parent = edit_bones['UpperArm']
        bpy.ops.object.mode_set(mode='OBJECT')
        index = {n['Name']: i for i, n in enumerate(partial)}
        return partial, index

    def test_keep_input_parent_reports_and_keeps_node(self):
        partial, index = self._reparented_input()
        nodes, plan = writer.merge_nodes(self.arm, copy.deepcopy(partial))
        self.assertEqual(plan.reparented, ['Hand'])
        self.assertEqual(nodes[index['Hand']], partial[index['Hand']])

    def test_blender_parent_keep_placement_keeps_world_matrix(self):
        partial, index = self._reparented_input()
        before = transforms.world_matrices(partial)[index['Hand']]
        nodes, _ = writer.merge_nodes(self.arm, partial,
                                      reparent=merge.BLENDER_KEEP_PLACEMENT)
        self.assertEqual(nodes[index['Hand']]['ParentIndex'], index['UpperArm'])
        after = transforms.world_matrices(nodes)[index['Hand']]
        for r in range(4):
            for c in range(4):
                self.assertAlmostEqual(after[r][c], before[r][c], places=5)

    def test_blender_parent_as_is_moves_the_node(self):
        partial, index = self._reparented_input()
        before = transforms.world_matrices(partial)[index['Hand']]
        nodes, _ = writer.merge_nodes(self.arm, partial, reparent=merge.BLENDER_AS_IS)
        self.assertEqual(nodes[index['Hand']]['ParentIndex'], index['UpperArm'])
        self.assertEqual(nodes[index['Hand']]['Translation'],
                         partial[index['Hand']]['Translation'])
        after = transforms.world_matrices(nodes)[index['Hand']]
        self.assertGreater((after.translation - before.translation).length, 0.1)

    def test_non_armature_raises(self):
        with self.assertRaises(ValueError):
            writer.merge_nodes(None, self.full)


if __name__ == '__main__':
    unittest.main()
