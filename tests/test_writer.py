# Tests for src.core.bounds and src.core.writer

import json
import os
import tempfile
import unittest

import helpers
from src.core import writer


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


class FlagsTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()

    def test_root_marked_as_mesh_by_default(self):
        nodes = writer.build_nodes(two_bone_armature())
        self.assertEqual([n['Flags'] for n in nodes], [12, 8])

    def test_root_plain_bone_when_option_off(self):
        nodes = writer.build_nodes(two_bone_armature(), mark_root_as_mesh=False)
        self.assertEqual([n['Flags'] for n in nodes], [8, 8])

    def test_non_armature_raises(self):
        with self.assertRaises(ValueError):
            writer.build_nodes(None)


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
