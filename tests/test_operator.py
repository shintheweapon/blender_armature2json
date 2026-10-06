# End-to-end test: register the extension and run the export operator

import json
import os
import tempfile
import unittest

import bpy

import helpers
import src


class ExportOperatorTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        src.register()

    def tearDown(self):
        src.unregister()

    def test_operator_writes_nodes_with_scene_options(self):
        arm = helpers.make_armature([
            ('Root', None, (0, 0, 0), (0, 1, 0), 0.0),
            ('Tip', 'Root', (0, 1, 0), (0, 2, 0), 0.0),
        ])
        bpy.context.view_layer.objects.active = arm
        bpy.context.scene.flver_node_export_mark_root_as_mesh = False
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'out.json')
            result = bpy.ops.flver_node_export.export(filepath=path)
            self.assertEqual(result, {'FINISHED'})
            with open(path, encoding='utf-8') as handle:
                nodes = json.load(handle)
        self.assertEqual([n['Name'] for n in nodes], ['Root', 'Tip'])
        self.assertEqual([n['Flags'] for n in nodes], [8, 8])
        self.assertEqual(nodes[1]['Translation'], {'X': 1, 'Y': 0, 'Z': 0})

    def test_operator_unavailable_without_armature(self):
        self.assertFalse(bpy.ops.flver_node_export.export.poll())

    def test_export_menu_entry_registered(self):
        names = [getattr(f, '__name__', '') for f in bpy.types.TOPBAR_MT_file_export._dyn_ui_initialize()]
        self.assertIn('menu_func_export', names)


if __name__ == '__main__':
    unittest.main()
