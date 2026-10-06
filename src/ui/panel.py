# Sidebar panel for FLVER node export

import bpy

from ..operators import find_armature


class FLVER_NODE_EXPORT_PT_main(bpy.types.Panel):
    """Export options and button in the 3D Viewport sidebar"""
    bl_label = "FLVER Node Export"
    bl_idname = "FLVER_NODE_EXPORT_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "FLVER Nodes"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        armature_obj = find_armature(context)

        box = layout.box()
        if armature_obj is None:
            box.alert = True
            box.label(text="No armature in the scene", icon='ERROR')
        else:
            box.label(text=f"Armature: {armature_obj.name}", icon='ARMATURE_DATA')

        col = layout.column(align=True)
        col.prop(scene, "flver_node_export_length_axis")
        col.prop(scene, "flver_node_export_roll_axis")
        layout.prop(scene, "flver_node_export_mark_root_as_mesh")

        row = layout.row()
        row.scale_y = 1.5
        row.operator("flver_node_export.export", text="Export", icon='EXPORT')


classes = (
    FLVER_NODE_EXPORT_PT_main,
)
