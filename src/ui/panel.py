# Sidebar panel for FLVER node export

import bpy

from ..operators import draw_options, find_armature


class ARMATURE2JSON_PT_main(bpy.types.Panel):
    """Export options and button in the 3D Viewport sidebar"""
    bl_label = "Armature2JSON"
    bl_idname = "ARMATURE2JSON_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature2JSON"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
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

        draw_options(layout, scene)

        row = layout.row()
        row.scale_y = 1.5
        row.operator("armature2json.export", text="Export", icon='EXPORT')


classes = (
    ARMATURE2JSON_PT_main,
)
