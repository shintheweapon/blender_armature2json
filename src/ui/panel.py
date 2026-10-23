# Sidebar panel for FLVER node export

import bpy

from .. import prefs
from ..operators import ARMATURE2JSON_OT_match_vanilla, draw_options, find_armature


class ARMATURE2JSON_PT_main(bpy.types.Panel):
    """Export options and button in the 3D Viewport sidebar"""
    bl_label = "Armature2JSON"
    bl_idname = "ARMATURE2JSON_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature2JSON"

    def draw(self, context):
        layout = self.layout
        armature_obj = find_armature(context)

        box = layout.box()
        if armature_obj is None:
            box.alert = True
            box.label(text="No armature in the scene", icon='ERROR')
        else:
            # Formatted text: translate the template, then fill it in
            text = bpy.app.translations.pgettext_iface("Armature: {name}")
            box.label(text=text.format(name=armature_obj.name), icon='ARMATURE_DATA',
                      translate=False)

        # Vanilla orientations on the armature, done before exporting
        options = prefs.get(context)
        box = layout.box()
        if options is not None:
            box.prop(options, "vanilla_reference_path")
        box.operator(ARMATURE2JSON_OT_match_vanilla.bl_idname)

        draw_options(layout, context)

        row = layout.row()
        row.scale_y = 1.5
        row.operator("armature2json.export", text="Export", icon='EXPORT')


classes = (
    ARMATURE2JSON_PT_main,
)
