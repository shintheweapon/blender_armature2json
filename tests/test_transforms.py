# Tests for src.core.transforms

import itertools
import math
import random
import unittest

from mathutils import Euler, Matrix, Vector

import helpers
from src.core import transforms


def assert_vectors_close(case, actual, expected, places=5):
    """Assert two vectors match component by component."""
    for a, e in zip(actual, expected):
        case.assertAlmostEqual(a, e, places=places)


class AxisMatrixTests(unittest.TestCase):

    def test_default_maps_bone_y_to_node_x_and_bone_z_to_node_minus_z(self):
        expected = Matrix(((0, 1, 0), (1, 0, 0), (0, 0, -1))).to_4x4()
        self.assertEqual(transforms.axis_matrix(), expected)

    def test_every_option_pair_puts_bone_axes_on_chosen_node_axes(self):
        for length, roll in itertools.permutations(transforms.AXES, 2):
            if length.strip('-') == roll.strip('-'):
                continue
            with self.subTest(length=length, roll=roll):
                k = transforms.axis_matrix(length, roll).to_3x3()
                self.assertAlmostEqual(k.determinant(), 1.0)
                # With bone axes = identity, node axes are the columns of k
                along = k @ transforms._AXIS_VECTORS[length]
                rolled = k @ transforms._AXIS_VECTORS[roll]
                assert_vectors_close(self, along, (0, 1, 0))
                assert_vectors_close(self, rolled, (0, 0, 1))

    def test_same_line_axes_raise(self):
        with self.assertRaises(ValueError):
            transforms.axis_matrix('X', '-X')

    def test_unknown_axis_raises(self):
        with self.assertRaises(ValueError):
            transforms.axis_matrix('W', 'Z')


class EulerTests(unittest.TestCase):

    def test_xzy_euler_equals_soulsformats_order(self):
        # Node.cs ComputeLocalTransform: Scale * RotX * RotZ * RotY * Translation
        # (row vectors), which is Ry @ Rz @ Rx for column vectors.
        rng = random.Random(1)
        for _ in range(50):
            x, y, z = (rng.uniform(-math.pi, math.pi) for _ in range(3))
            expected = (Matrix.Rotation(y, 3, 'Y') @ Matrix.Rotation(z, 3, 'Z')
                        @ Matrix.Rotation(x, 3, 'X'))
            actual = Euler((x, y, z), 'XZY').to_matrix()
            for row_a, row_e in zip(actual, expected):
                assert_vectors_close(self, row_a, row_e)

    def test_euler_extraction_is_exact_near_and_at_gimbal_lock(self):
        # Z close to or at +-90 degrees makes X and Y hard to separate; the
        # rebuilt rotation must still match the input closely.
        rng = random.Random(3)
        for offset in (1e-2, 1e-4, 1e-6, 0.0):
            for sign in (1, -1):
                for _ in range(20):
                    x, y = rng.uniform(-math.pi, math.pi), rng.uniform(-math.pi, math.pi)
                    z = sign * (math.pi / 2 - offset)
                    matrix = Euler((x, y, z), 'XZY').to_matrix()
                    angles = transforms.matrix_to_euler_xzy(matrix)
                    rebuilt = transforms.euler_xzy_to_rows(angles)
                    error = max(abs(a - b) for ra, rb in zip(rebuilt, matrix)
                                for a, b in zip(ra, rb))
                    self.assertLess(error, 1e-6, (offset, sign, x, y))

    def test_euler_extraction_of_single_precision_rotation_near_gimbal_lock(self):
        # Root node rotation of a vanilla skeleton imported into Blender: Z is
        # within 1e-4 of 90 degrees and the matrix carries float32 rounding.
        # Matrix.to_euler('XZY') rebuilds this with an error near 1e-3.
        from mathutils import Quaternion
        quat = Quaternion((2.824298462655861e-05, -0.7071067094802856,
                           -0.7071068286895752, -2.9529863240895793e-05))
        matrix = quat.to_matrix()
        rebuilt = transforms.euler_xzy_to_rows(transforms.matrix_to_euler_xzy(matrix))
        error = max(abs(a - b) for ra, rb in zip(rebuilt, matrix) for a, b in zip(ra, rb))
        self.assertLess(error, 1e-6)

    def test_local_trs_round_trip(self):
        rng = random.Random(2)
        for _ in range(50):
            angles = [rng.uniform(-math.pi, math.pi) for _ in range(3)]
            loc = Vector([rng.uniform(-2, 2) for _ in range(3)])
            matrix = Matrix.LocRotScale(loc, Euler(angles, 'XZY'), None)
            translation, rotation, scale = transforms.local_trs(None, matrix)
            rebuilt = Matrix.LocRotScale(translation, Euler(rotation, 'XZY'), scale)
            for row_a, row_e in zip(rebuilt, matrix):
                assert_vectors_close(self, row_a, row_e)


class NodeMatrixTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_upright_bone_points_up_in_flver_space(self):
        arm = helpers.make_armature([('Root', None, (0.5, 0.2, 1.0), (0.5, 0.2, 2.0), 0.0)])
        bone = arm.data.bones['Root']
        node = transforms.node_matrix(transforms.space_mapping('BLENDER_WORLD', arm.matrix_world), arm.matrix_world,
                                      bone.matrix_local, transforms.axis_matrix())
        # Blender (x, y, z) lands at FLVER (x, z, y): Y-up, then Z mirrored
        assert_vectors_close(self, node.translation, (0.5, 1.0, 0.2))
        assert_vectors_close(self, node.col[0].xyz, (0, 1, 0))

    def test_armature_object_transform_is_applied(self):
        # Bone along armature +Y, armature turned +90 degrees about X: the bone
        # points up in the scene, as in files imported from FLVER_Editor FBX.
        arm = helpers.make_armature([('Root', None, (0, 0, 0), (0, 1, 0), 0.0)])
        arm.rotation_euler = (math.pi / 2, 0, 0)
        bpy_update()
        bone = arm.data.bones['Root']
        node = transforms.node_matrix(transforms.space_mapping('BLENDER_WORLD', arm.matrix_world), arm.matrix_world,
                                      bone.matrix_local, transforms.axis_matrix())
        assert_vectors_close(self, node.col[0].xyz, (0, 1, 0))

    def test_child_offset_lies_on_length_axis(self):
        arm = helpers.make_armature([
            ('Parent', None, (0, 0, 0), (0, 0, 1), 0.0),
            ('Child', 'Parent', (0, 0, 1), (0, 0, 2), 0.0),
        ])
        axes = transforms.axis_matrix()
        world = transforms.space_mapping('BLENDER_WORLD', arm.matrix_world)
        parent = transforms.node_matrix(world, arm.matrix_world,
                                        arm.data.bones['Parent'].matrix_local, axes)
        child = transforms.node_matrix(world, arm.matrix_world,
                                       arm.data.bones['Child'].matrix_local, axes)
        translation, rotation, scale = transforms.local_trs(parent, child)
        assert_vectors_close(self, translation, (1, 0, 0))
        assert_vectors_close(self, rotation, (0, 0, 0))
        assert_vectors_close(self, scale, (1, 1, 1))


class SpaceTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_armature_space_is_the_bone_matrix_with_the_axes(self):
        arm = helpers.make_armature([('Root', None, (0.1, 0.9, -0.2), (0.4, 1.3, 0.1), 0.7)])
        arm.rotation_euler = (0.4, -1.1, 2.0)
        arm.location = (3.0, -2.0, 1.0)
        bpy_update()
        bone = arm.data.bones['Root']
        axes = transforms.axis_matrix('Y', 'Z')
        space = transforms.space_mapping('ARMATURE', arm.matrix_world)
        node = transforms.node_matrix(space, arm.matrix_world, bone.matrix_local, axes)
        expected = bone.matrix_local @ axes
        for row, row_expected in zip(node, expected):
            assert_vectors_close(self, row, row_expected)

    def test_armature_space_points_are_in_the_armature_space(self):
        world = Matrix.Translation((1.0, 2.0, 3.0)) @ Euler((0.3, 0.2, 0.1)).to_matrix().to_4x4()
        space = transforms.space_mapping('ARMATURE', world)
        point = Vector((0.5, -0.25, 2.0))
        assert_vectors_close(self, transforms.point_to_flver(space, world, point), point)

    def test_blender_world_is_the_previous_mapping(self):
        world = Euler((math.pi / 2, 0.0, 0.3)).to_matrix().to_4x4()
        bone = Matrix.Translation((0.1, 0.2, 0.3)) @ Euler((0.5, -0.4, 1.0)).to_matrix().to_4x4()
        axes = transforms.axis_matrix()
        space = transforms.space_mapping('BLENDER_WORLD', world)
        node = transforms.node_matrix(space, world, bone, axes)
        expected = (transforms.MIRROR_Z @ transforms.Y_UP @ world @ bone
                    @ transforms.MIRROR_Z @ axes)
        for row, row_expected in zip(node, expected):
            assert_vectors_close(self, row, row_expected)

    def test_unknown_space_raises(self):
        with self.assertRaises(ValueError):
            transforms.space_mapping('SIDEWAYS', Matrix.Identity(4))


def bpy_update():
    """Refresh object matrices after changing transforms."""
    import bpy
    bpy.context.view_layer.update()


if __name__ == '__main__':
    unittest.main()
