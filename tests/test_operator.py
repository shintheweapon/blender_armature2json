# End-to-end test: register the extension and run the export operator

import json
import os
import tempfile
import unittest

import bpy

import helpers
import src
from src.core import writer


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

    def _merge_setup(self, folder):
        """An armature with a Cloth bone, and a reference JSON that lacks it."""
        arm = helpers.make_armature([
            ('Root', None, (0, 0, 0), (0, 1, 0), 0.0),
            ('Tip', 'Root', (0, 1, 0), (0, 2, 0), 0.0),
            ('Cloth', 'Root', (0.5, 1, 0), (0.5, 1, -1), 0.0),
        ])
        bpy.context.view_layer.objects.active = arm
        nodes = [n for n in writer.build_nodes(arm, mark_root_as_mesh=False)
                 if n['Name'] != 'Cloth']
        for n in nodes:
            n['FirstChildIndex'] = n['NextSiblingIndex'] = n['PreviousSiblingIndex'] = -1
        input_path = os.path.join(folder, 'input.json')
        writer.write_nodes(input_path, nodes)
        scene = bpy.context.scene
        scene.flver_node_export_mode = 'MERGE'
        scene.flver_node_export_input_path = input_path
        return input_path

    def test_merge_mode_writes_merged_file(self):
        with tempfile.TemporaryDirectory() as folder:
            self._merge_setup(folder)
            path = os.path.join(folder, 'out.json')
            result = bpy.ops.flver_node_export.export(filepath=path)
            self.assertEqual(result, {'FINISHED'})
            with open(path, encoding='utf-8') as handle:
                nodes = json.load(handle)
        self.assertEqual([n['Name'] for n in nodes], ['Root', 'Tip', 'Cloth'])
        self.assertEqual(nodes[2]['ParentIndex'], 0)
        self.assertEqual(nodes[1]['NextSiblingIndex'], 2)

    def test_merge_mode_without_input_path_cancels(self):
        with tempfile.TemporaryDirectory() as folder:
            self._merge_setup(folder)
            bpy.context.scene.flver_node_export_input_path = ''
            path = os.path.join(folder, 'out.json')
            with self.assertRaisesRegex(RuntimeError, 'Choose a reference JSON'):
                bpy.ops.flver_node_export.export(filepath=path)
            self.assertFalse(os.path.exists(path))

    def test_merge_mode_with_invalid_input_cancels(self):
        with tempfile.TemporaryDirectory() as folder:
            input_path = self._merge_setup(folder)
            path = os.path.join(folder, 'out.json')
            with open(input_path, 'w', encoding='utf-8') as handle:
                handle.write('{"Name": "Root"}')
            with self.assertRaisesRegex(RuntimeError, 'must be a list'):
                bpy.ops.flver_node_export.export(filepath=path)
            with open(input_path, 'w', encoding='utf-8') as handle:
                handle.write('[not json')
            with self.assertRaisesRegex(RuntimeError, 'not valid JSON'):
                bpy.ops.flver_node_export.export(filepath=path)
            bpy.context.scene.flver_node_export_input_path = os.path.join(folder, 'missing.json')
            with self.assertRaisesRegex(RuntimeError, 'Could not read the reference JSON'):
                bpy.ops.flver_node_export.export(filepath=path)
            self.assertFalse(os.path.exists(path))

    def test_merge_mode_refuses_to_overwrite_the_input(self):
        with tempfile.TemporaryDirectory() as folder:
            input_path = self._merge_setup(folder)
            with open(input_path, 'rb') as handle:
                before = handle.read()
            targets = [input_path]
            if os.name == 'nt':
                targets.append(input_path.upper())
            for target in targets:
                with self.assertRaisesRegex(RuntimeError, 'would overwrite the reference JSON'):
                    bpy.ops.flver_node_export.export(filepath=target)
            with open(input_path, 'rb') as handle:
                self.assertEqual(handle.read(), before)
            self.assertEqual(sorted(os.listdir(folder)), ['input.json'])

    def test_new_properties_registered_with_tooltips(self):
        properties = bpy.types.Scene.bl_rna.properties
        for name in ('flver_node_export_mode', 'flver_node_export_input_path',
                     'flver_node_export_reparent'):
            self.assertIn(name, properties)
            self.assertTrue(properties[name].description, name)
        for name in ('flver_node_export_mode', 'flver_node_export_reparent'):
            for item in properties[name].enum_items:
                self.assertTrue(item.description, f'{name}.{item.identifier}')
        self.assertEqual(properties['flver_node_export_mode'].default, 'ARMATURE')
        self.assertEqual(properties['flver_node_export_reparent'].default, 'KEEP_INPUT')

    def test_operator_unavailable_without_armature(self):
        self.assertFalse(bpy.ops.flver_node_export.export.poll())

    def test_export_menu_entry_registered(self):
        names = [getattr(f, '__name__', '') for f in bpy.types.TOPBAR_MT_file_export._dyn_ui_initialize()]
        self.assertIn('menu_func_export', names)


if __name__ == '__main__':
    unittest.main()
