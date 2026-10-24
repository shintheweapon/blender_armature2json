# Tests for Match Vanilla Orientations: the inverse of the export mapping,
# turning the armature's bones, and the operator with the remembered path

import json
import os
import tempfile
import unittest

import bpy
from mathutils import Euler, Matrix

import helpers
import src
from src.core import orientations, transforms, writer
from test_operator import PACKAGE, add_preferences_entry

SETTINGS = [(space, axes) for space in transforms.SPACES for axes in (('X', '-Z'), ('Y', 'Z'))]


def largest_difference(a: Matrix, b: Matrix) -> float:
    return max(abs(x - y) for row_a, row_b in zip(a, b) for x, y in zip(row_a, row_b))


def sample_armature():
    """A turned armature with a chain, a side branch and a connected child."""
    arm = helpers.make_armature([
        ('Pelvis', None, (0.0, 0.0, 1.0), (0.0, 0.1, 1.1), 0.3),
        ('Spine', 'Pelvis', (0.0, 0.1, 1.1), (0.0, 0.1, 1.4), -0.5),
        ('Head', 'Spine', (0.0, 0.1, 1.4), (0.05, 0.0, 1.6), 1.1),
        ('Cloth', 'Pelvis', (0.2, -0.1, 1.0), (0.3, -0.2, 0.7), 0.0),
    ])
    arm.rotation_euler = (1.5708, 0.0, 0.4)
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    arm.data.edit_bones['Spine'].use_connect = True
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm


REFERENCE = {
    'Pelvis': Euler((0.2, 1.3, -0.4)).to_matrix(),
    'Spine': Euler((1.0, -0.2, 0.6)).to_matrix(),
    'Head': Euler((-0.7, 0.4, 2.1)).to_matrix(),
}


def export_rotations(arm, space, axes):
    nodes = writer.build_nodes(arm, length_axis=axes[0], roll_axis=axes[1], space=space)
    worlds = transforms.world_matrices(nodes)
    return {n['Name']: w.to_3x3().normalized() for n, w in zip(nodes, worlds)}


class InverseTests(unittest.TestCase):

    def test_bone_rotation_round_trips_through_the_export_mapping(self):
        world = Matrix.Translation((0.3, -0.2, 0.5)) @ Euler((1.4, 0.1, -0.6)).to_matrix().to_4x4()
        for space_name, (length, roll) in SETTINGS:
            space = transforms.space_mapping(space_name, world)
            axes = transforms.axis_matrix(length, roll)
            for node_rotation in REFERENCE.values():
                rotation = orientations.bone_rotation_for_node(space, world, node_rotation, axes)
                bone = rotation.to_4x4()
                bone.translation = (0.1, 0.2, 0.3)
                node = transforms.node_matrix(space, world, bone, axes)
                with self.subTest(space=space_name, axes=(length, roll)):
                    self.assertAlmostEqual(rotation.determinant(), 1.0, places=5)
                    self.assertLess(largest_difference(node.to_3x3(), node_rotation), 1e-5)


class MatchTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def match(self, arm, space_name, axes):
        space = transforms.space_mapping(space_name, arm.matrix_world)
        return orientations.match_orientations(
            arm, REFERENCE, space, transforms.axis_matrix(*axes))

    def test_export_writes_the_reference_rotations(self):
        for space_name, axes in SETTINGS:
            helpers.new_scene()
            arm = sample_armature()
            heads = {b.name: b.head_local.copy() for b in arm.data.bones}
            cloth = arm.data.bones['Cloth'].matrix_local.copy()
            matched = self.match(arm, space_name, axes)
            rotations = export_rotations(arm, space_name, axes)
            with self.subTest(space=space_name, axes=axes):
                self.assertEqual(matched, ['Head', 'Pelvis', 'Spine'])
                for name, rotation in REFERENCE.items():
                    self.assertLess(largest_difference(rotations[name], rotation), 1e-5, name)
                for bone in arm.data.bones:
                    self.assertLess((bone.head_local - heads[bone.name]).length, 1e-6, bone.name)
                self.assertLess(largest_difference(arm.data.bones['Cloth'].matrix_local, cloth), 1e-6)

    def test_connected_child_is_disconnected_and_stays(self):
        arm = sample_armature()
        before = arm.data.bones['Spine'].matrix_local.copy()
        space = transforms.space_mapping('ARMATURE', arm.matrix_world)
        orientations.match_orientations(arm, {'Pelvis': REFERENCE['Pelvis']}, space,
                                        transforms.axis_matrix('Y', 'Z'))
        self.assertFalse(arm.data.bones['Spine'].use_connect)
        self.assertLess(largest_difference(arm.data.bones['Spine'].matrix_local, before), 1e-6)

    def test_x_axis_mirror_does_not_copy_one_side_onto_the_other(self):
        arm = helpers.make_armature([
            ('R_Arm', None, (-0.2, 0.0, 1.0), (-0.5, 0.0, 1.0), 0.0),
            ('R_Hand', 'R_Arm', (-0.5, 0.0, 1.0), (-0.7, 0.0, 1.0), 0.0),
            ('L_Arm', None, (0.2, 0.0, 1.0), (0.5, 0.0, 1.0), 0.0),
            ('L_Hand', 'L_Arm', (0.5, 0.0, 1.0), (0.7, 0.0, 1.0), 0.0),
        ])
        arm.data.use_mirror_x = True
        heads = {b.name: b.head_local.copy() for b in arm.data.bones}
        reference = {
            'R_Arm': Euler((-0.3, 1.0, 0.6)).to_matrix(),
            'R_Hand': Euler((1.2, 0.4, 0.2)).to_matrix(),
            'L_Arm': Euler((0.3, 1.0, -0.6)).to_matrix(),
            'L_Hand': Euler((1.2, -0.4, 0.2)).to_matrix(),
        }
        space = transforms.space_mapping('ARMATURE', arm.matrix_world)
        orientations.match_orientations(arm, reference, space, transforms.axis_matrix('Y', 'Z'))
        for bone in arm.data.bones:
            self.assertLess(largest_difference(bone.matrix_local.to_3x3(), reference[bone.name]),
                            1e-5, bone.name)
            self.assertLess((bone.head_local - heads[bone.name]).length, 1e-6, bone.name)
        self.assertTrue(arm.data.use_mirror_x)

    def test_skinned_mesh_at_rest_keeps_its_shape(self):
        arm = sample_armature()
        box = helpers.make_skinned_box(arm, 'Spine', (0.2, 0.2, 0.3))

        def evaluated():
            depsgraph = bpy.context.evaluated_depsgraph_get()
            return [v.co.copy() for v in box.evaluated_get(depsgraph).data.vertices]

        before = evaluated()
        self.match(arm, 'BLENDER_WORLD', ('X', '-Z'))
        after = evaluated()
        self.assertLess(max((a - b).length for a, b in zip(before, after)), 1e-5)

    def test_mode_mirror_and_active_object_restored(self):
        arm = sample_armature()
        other = helpers.make_armature([('Bone', None, (0, 0, 0), (0, 1, 0), 0.0)], name='Other')
        bpy.context.view_layer.objects.active = other
        arm.data.use_mirror_x = True
        self.match(arm, 'ARMATURE', ('Y', 'Z'))
        self.assertIs(bpy.context.view_layer.objects.active, other)
        self.assertEqual(arm.mode, 'OBJECT')
        self.assertTrue(arm.data.use_mirror_x)

    def test_load_reference_reads_the_written_rotations(self):
        arm = sample_armature()
        nodes = writer.build_nodes(arm)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = os.path.join(folder.name, 'Nodes.json')
        with open(path, 'w', encoding='utf-8-sig') as handle:
            json.dump(nodes, handle)
        loaded = orientations.load_reference(path)
        expected = export_rotations(arm, transforms.DEFAULT_SPACE, ('X', '-Z'))
        self.assertEqual(sorted(loaded), sorted(expected))
        for name, rotation in loaded.items():
            self.assertLess(largest_difference(rotation, expected[name]), 1e-5, name)


class MatchOperatorTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        src.register()
        self.addCleanup(src.unregister)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = folder.name

    def write_reference(self):
        nodes = [{'Name': name, 'ParentIndex': -1,
                  'Translation': {'X': 0, 'Y': 0, 'Z': 0},
                  'Rotation': dict(zip('XYZ', transforms.matrix_to_euler_xzy(rotation))),
                  'Scale': {'X': 1, 'Y': 1, 'Z': 1}}
                 for name, rotation in REFERENCE.items()]
        path = os.path.join(self.folder, 'Nodes.json')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(nodes, handle)
        return path

    def test_operator_uses_the_remembered_path_and_the_panel_settings(self):
        arm = sample_armature()
        add_preferences_entry(self).vanilla_reference_path = self.write_reference()
        scene = bpy.context.scene
        scene.armature2json_space = 'ARMATURE'
        bpy.ops.armature2json.axes_as_imported()
        self.assertEqual((scene.armature2json_length_axis, scene.armature2json_roll_axis),
                         ('Y', 'Z'))
        self.assertEqual(bpy.ops.armature2json.match_vanilla(), {'FINISHED'})
        rotations = export_rotations(arm, 'ARMATURE', ('Y', 'Z'))
        for name, rotation in REFERENCE.items():
            self.assertLess(largest_difference(rotations[name], rotation), 1e-5, name)

    def test_without_a_path_reports_and_changes_nothing(self):
        arm = sample_armature()
        before = [b.matrix_local.copy() for b in arm.data.bones]
        add_preferences_entry(self)
        with self.assertRaisesRegex(RuntimeError, 'Vanilla Reference JSON'):
            bpy.ops.armature2json.match_vanilla()
        for bone, matrix in zip(arm.data.bones, before):
            self.assertLess(largest_difference(bone.matrix_local, matrix), 1e-9)

    def test_unreadable_file_reported(self):
        sample_armature()
        add_preferences_entry(self).vanilla_reference_path = os.path.join(self.folder, 'none.json')
        with self.assertRaisesRegex(RuntimeError, 'Could not read'):
            bpy.ops.armature2json.match_vanilla()

    def test_not_a_node_list_reported(self):
        sample_armature()
        path = os.path.join(self.folder, 'bad.json')
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump({'Name': 'Pelvis'}, handle)
        add_preferences_entry(self).vanilla_reference_path = path
        with self.assertRaisesRegex(RuntimeError, 'list of nodes'):
            bpy.ops.armature2json.match_vanilla()


if __name__ == '__main__':
    unittest.main()
