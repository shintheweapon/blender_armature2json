# Tests for the add-on's Simplified Chinese registration, which needs Blender;
# the table itself is checked in tests/unit/test_i18n.py

import os
import tempfile
import unittest

import bpy

import helpers
import src
from src import operators, ui
from src.core import i18n_zh_hans

ADDON_PROPERTIES = ('flver_node_export_mode', 'flver_node_export_input_path',
                    'flver_node_export_reparent', 'flver_node_export_length_axis',
                    'flver_node_export_roll_axis', 'flver_node_export_mark_root_as_mesh')


class ChineseTests(unittest.TestCase):

    def setUp(self):
        helpers.new_scene()
        src.register()
        view = bpy.context.preferences.view
        self.saved = (view.language, view.use_translate_interface,
                      view.use_translate_tooltips, view.use_translate_reports)
        self.table = i18n_zh_hans.table()

    def tearDown(self):
        view = bpy.context.preferences.view
        (view.language, view.use_translate_interface,
         view.use_translate_tooltips, view.use_translate_reports) = self.saved
        src.unregister()

    def chinese(self):
        view = bpy.context.preferences.view
        view.language = 'zh_HANS'
        view.use_translate_interface = True
        view.use_translate_tooltips = True
        view.use_translate_reports = True

    def test_every_interface_text_has_an_entry(self):
        texts = []
        properties = bpy.types.Scene.bl_rna.properties
        for name in ADDON_PROPERTIES:
            prop = properties[name]
            texts += [prop.name, prop.description]
            if prop.type == 'ENUM':
                for item in prop.enum_items:
                    if item.name not in ('X', 'Y', 'Z', '-X', '-Y', '-Z'):
                        texts.append(item.name)
                    texts.append(item.description)
        for panel in ui.classes:
            texts += [panel.bl_label, panel.bl_category, "No armature in the scene",
                      "Armature: {name}"]
        operator = operators.FLVER_NODE_EXPORT_OT_export
        texts += [operator.bl_label, operator.__doc__, "FLVER Nodes JSON (.json)"]
        missing = [t for t in texts if (i18n_zh_hans.DEFAULT, t) not in self.table]
        self.assertEqual(missing, [])

    def test_texts_show_in_chinese(self):
        self.chinese()
        tr = bpy.app.translations
        self.assertEqual(tr.pgettext_iface("Reference JSON"), "参考 JSON")
        self.assertEqual(tr.pgettext_iface("Export FLVER Nodes JSON", "Operator"),
                         "导出 FLVER 节点 JSON")
        self.assertEqual(tr.pgettext_tip("Build every node from the armature. "
                                         "No reference JSON is needed"),
                         "所有节点都由骨架生成，不需要参考 JSON")

    def test_error_report_in_chinese(self):
        arm = helpers.make_armature([('Root', None, (0, 0, 0), (0, 1, 0), 0.0)])
        bpy.context.view_layer.objects.active = arm
        with tempfile.TemporaryDirectory() as folder:
            reference = os.path.join(folder, 'reference.json')
            with open(reference, 'w', encoding='utf-8') as handle:
                handle.write('{"Name": "Root"}')
            scene = bpy.context.scene
            scene.flver_node_export_mode = 'MERGE'
            scene.flver_node_export_input_path = reference
            self.chinese()
            with self.assertRaisesRegex(RuntimeError, '参考 JSON 应为节点列表'):
                bpy.ops.flver_node_export.export(filepath=os.path.join(folder, 'out.json'))

    def test_export_succeeds_and_its_report_template_is_chinese(self):
        arm = helpers.make_armature([('Root', None, (0, 0, 0), (0, 1, 0), 0.0)])
        bpy.context.view_layer.objects.active = arm
        self.chinese()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, 'out.json')
            self.assertEqual(bpy.ops.flver_node_export.export(filepath=path), {'FINISHED'})
        # The report text itself is not returned by bpy.ops; check the template
        text = bpy.app.translations.pgettext_rpt(
            "Exported {count} nodes from '{armature}' to {path}")
        self.assertEqual(text.format(count=1, armature=arm.name, path='p'),
                         f"已从骨架“{arm.name}”导出 1 个节点到 p")

    def test_english_again_after_unregister(self):
        self.chinese()
        src.unregister()
        try:
            self.assertEqual(bpy.app.translations.pgettext_iface("Reference JSON"),
                             "Reference JSON")
        finally:
            src.register()

    def test_reports_stay_english_when_report_translation_is_off(self):
        self.chinese()
        bpy.context.preferences.view.use_translate_reports = False
        self.assertEqual(bpy.app.translations.pgettext_rpt(
            "Could not write the file: {error}"), "Could not write the file: {error}")


if __name__ == '__main__':
    unittest.main()
