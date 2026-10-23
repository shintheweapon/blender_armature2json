# Tests for src.core.bounds and src.core.writer

import json
import math
import os
import tempfile
import unittest

import bpy
from mathutils import Quaternion

import helpers
from src.core import vanilla_axes, writer
from src.core.transforms import point_to_flver, space_mapping, world_matrices


def two_bone_armature():
    """Bone 'Root' along Blender +Y at the origin, with an unweighted child."""
    return helpers.make_armature([
        ('Root', None, (0, 0, 0), (0, 1, 0), 0.0),
        ('Tip', 'Root', (0, 1, 0), (0, 2, 0), 0.0),
    ])


class BoundsTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_box_is_weighted_extent_in_node_axes(self):
        arm = two_bone_armature()
        helpers.make_skinned_box(arm, 'Root', (1.0, 2.0, 3.0))
        root = writer.build_nodes(arm)[0]
        # Worked by hand for default axes: a Blender point (x, y, z) sits at
        # (y, x, z) in Root's node axes, so the box spans (0..2, 0..1, 0..3).
        self.assertEqual(root['BoundingBoxMin'], {'X': 0, 'Y': 0, 'Z': 0})
        self.assertEqual(root['BoundingBoxMax'], {'X': 2, 'Y': 1, 'Z': 3})

    def test_unweighted_bone_and_zero_weights_give_no_extent(self):
        arm = two_bone_armature()
        box = helpers.make_skinned_box(arm, 'Root', (1.0, 2.0, 3.0))
        far = box.vertex_groups.new(name='Tip')
        far.add([0, 7], 0.0, 'REPLACE')
        tip = writer.build_nodes(arm)[1]
        self.assertEqual(tip['BoundingBoxMin'], {'X': 0, 'Y': 0, 'Z': 0})
        self.assertEqual(tip['BoundingBoxMax'], {'X': 0, 'Y': 0, 'Z': 0})


def turned_spine_armature():
    """
    Vanilla-named bones Spine > Neck > Head pointing along Blender +X (not the
    vanilla way), and a custom bone Ear under Head, rolled 30 degrees.
    """
    return helpers.make_armature([
        ('Spine', None, (0, 0, 1.0), (0.2, 0, 1.0), 0.0),
        ('Neck', 'Spine', (0.2, 0, 1.4), (0.3, 0, 1.4), 0.4),
        ('Head', 'Neck', (0.3, 0, 1.5), (0.5, 0, 1.5), 1.0),
        ('Ear', 'Head', (0.4, 0.1, 1.6), (0.4, 0.2, 1.6), 0.5),
    ])


class VanillaOrientationTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        self.arm = turned_spine_armature()
        self.box = helpers.make_skinned_box(self.arm, 'Head', (0.3, 0.2, 0.25))
        self.plain = writer.build_nodes(self.arm, vanilla_orientations=False)
        self.turned = writer.build_nodes(self.arm, vanilla_orientations=True)
        self.plain_worlds = world_matrices(self.plain)
        self.turned_worlds = world_matrices(self.turned)

    def angle(self, matrix, name):
        """Degrees between a node's world orientation and the table's."""
        difference = matrix.to_quaternion().rotation_difference(
            Quaternion(vanilla_axes.ORIENTATIONS[name]))
        degrees = math.degrees(difference.angle)
        return min(degrees, 360.0 - degrees)

    def test_vanilla_names_take_the_table_orientation(self):
        for i, node in enumerate(self.turned):
            if node['Name'] in vanilla_axes.ORIENTATIONS:
                with self.subTest(node=node['Name']):
                    self.assertLess(self.angle(self.turned_worlds[i], node['Name']), 1e-3)
        # Before: at least one of them was far off
        self.assertGreater(max(self.angle(self.plain_worlds[i], n['Name'])
                               for i, n in enumerate(self.plain)
                               if n['Name'] in vanilla_axes.ORIENTATIONS), 10.0)

    def test_positions_do_not_move(self):
        for a, b in zip(self.plain_worlds, self.turned_worlds):
            self.assertLess((a.translation - b.translation).length, 1e-5)

    def test_custom_bone_keeps_its_world_matrix(self):
        i = [n['Name'] for n in self.turned].index('Ear')
        self.assertNotIn('Ear', vanilla_axes.ORIENTATIONS)
        difference = self.plain_worlds[i] - self.turned_worlds[i]
        self.assertLess(max(abs(v) for row in difference for v in row), 1e-5)

    def test_weighted_points_stay_inside_the_turned_box(self):
        i = [n['Name'] for n in self.turned].index('Head')
        box_min = self.turned[i]['BoundingBoxMin']
        box_max = self.turned[i]['BoundingBoxMax']
        inverse = self.turned_worlds[i].inverted()
        for vertex in self.box.data.vertices:
            local = inverse @ point_to_flver(space_mapping('BLENDER_WORLD', self.arm.matrix_world),
                                             self.box.matrix_world, vertex.co)
            for k, axis in enumerate('XYZ'):
                self.assertGreaterEqual(local[k], box_min[axis] - 1e-5)
                self.assertLessEqual(local[k], box_max[axis] + 1e-5)

    def test_off_gives_the_plain_output(self):
        again = writer.build_nodes(self.arm, vanilla_orientations=False)
        self.assertEqual(again, self.plain)
        self.assertNotEqual(self.turned, self.plain)


class FlagsTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_root_plain_bone_by_default(self):
        nodes = writer.build_nodes(two_bone_armature())
        self.assertEqual([n['Flags'] for n in nodes], [8, 8])

    def test_root_marked_as_mesh_when_option_on(self):
        nodes = writer.build_nodes(two_bone_armature(), mark_root_as_mesh=True)
        self.assertEqual([n['Flags'] for n in nodes], [12, 8])

    def test_root_plain_bone_when_option_off(self):
        nodes = writer.build_nodes(two_bone_armature(), mark_root_as_mesh=False)
        self.assertEqual([n['Flags'] for n in nodes], [8, 8])

    def test_non_armature_raises(self):
        with self.assertRaises(ValueError):
            writer.build_nodes(None)


class ArmatureSpaceTests(unittest.TestCase):
    """Coordinate Space 'Armature Space = FS Space': the armature's own coordinates."""

    def setUp(self):
        helpers.new_scene()
        self.arm = helpers.make_armature([
            ('Root', None, (0.0, 0.9, 0.0), (0.0, 1.2, 0.0), 0.0),
            ('Head', 'Root', (0.0, 1.2, 0.0), (0.0, 1.5, 0.1), 0.3),
        ])
        self.box = helpers.make_skinned_box(self.arm, 'Head', (0.2, 0.3, 0.1))

    def export(self, **options):
        return writer.build_nodes(self.arm, space='ARMATURE', mark_root_as_mesh=False,
                                  vanilla_orientations=False, **options)

    def test_root_position_is_the_armature_space_head(self):
        root = self.export()[0]
        for axis, value in zip('XYZ', (0.0, 0.9, 0.0)):
            self.assertAlmostEqual(root['Translation'][axis], value, places=6)

    def test_object_transform_is_ignored(self):
        plain = self.export()
        self.arm.rotation_euler = (math.pi / 2, 0.0, 0.5)
        self.arm.location = (1.0, 2.0, 3.0)
        bpy.context.view_layer.update()
        # The mesh moves with the armature, as a child object would
        self.box.matrix_world = self.arm.matrix_world.copy()
        bpy.context.view_layer.update()
        turned = self.export()
        for a, b in zip(plain, turned):
            for key in ('Translation', 'Rotation', 'BoundingBoxMin', 'BoundingBoxMax'):
                for axis in 'XYZ':
                    self.assertAlmostEqual(a[key][axis], b[key][axis], places=5, msg=(a['Name'], key))

    def test_boxes_hold_the_weighted_points(self):
        nodes = self.export()
        worlds = world_matrices(nodes)
        i = [n['Name'] for n in nodes].index('Head')
        space = space_mapping('ARMATURE', self.arm.matrix_world)
        inverse = worlds[i].inverted()
        for vertex in self.box.data.vertices:
            local = inverse @ point_to_flver(space, self.box.matrix_world, vertex.co)
            for k, axis in enumerate('XYZ'):
                self.assertGreaterEqual(local[k], nodes[i]['BoundingBoxMin'][axis] - 1e-5)
                self.assertLessEqual(local[k], nodes[i]['BoundingBoxMax'][axis] + 1e-5)

    def test_merge_adds_bones_in_armature_space(self):
        full = self.export()
        partial = [dict(full[0], FirstChildIndex=-1)]
        nodes, _ = writer.merge_nodes(self.arm, partial, space='ARMATURE')
        added = [n for n in nodes if n['Name'] == 'Head'][0]
        for key in ('Translation', 'Rotation'):
            for axis in 'XYZ':
                self.assertAlmostEqual(added[key][axis], full[1][key][axis], places=5)


class OutputTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_written_file_parses_back_and_matches_vanilla_layout(self):
        nodes = writer.build_nodes(two_bone_armature())
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'nodes.json')
            writer.write_nodes(path, nodes)
            raw = open(path, 'rb').read()
        self.assertEqual(json.loads(raw), nodes)
        self.assertFalse(raw.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b' ', raw)
        self.assertEqual(list(nodes[0]), [
            'Name', 'ParentIndex', 'FirstChildIndex', 'NextSiblingIndex',
            'PreviousSiblingIndex', 'Translation', 'Rotation', 'Scale',
            'BoundingBoxMin', 'BoundingBoxMax', 'Flags'])
        self.assertIn(b'"Scale":{"X":1,"Y":1,"Z":1}', raw)

    def test_number_rounding(self):
        self.assertEqual(writer._number(1.0), 1)
        self.assertEqual(writer._number(-0.0), 0)
        self.assertEqual(writer._number(0.30000001192092896), 0.300000012)


if __name__ == '__main__':
    unittest.main()
