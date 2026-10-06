# Operator that exports the FLVER node JSON

from typing import Optional

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..core import writer


def find_armature(context: bpy.types.Context) -> Optional[bpy.types.Object]:
    """
    Pick the armature to export.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.

    Returns
    -------
    bpy.types.Object or None
        The active object when it is an armature, otherwise the first
        armature in the scene, or None when the scene has none.
    """
    active = context.view_layer.objects.active
    if active is not None and active.type == 'ARMATURE':
        return active
    return next((obj for obj in context.scene.objects
                 if obj.type == 'ARMATURE'), None)


class FLVER_NODE_EXPORT_OT_export(bpy.types.Operator, ExportHelper):
    """Export the armature's bones as a FLVER node JSON for FLVER_Editor"""
    bl_idname = "flver_node_export.export"
    bl_label = "Export FLVER Nodes JSON"
    bl_options = {'REGISTER'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return find_armature(context) is not None

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.prop(scene, "flver_node_export_length_axis")
        layout.prop(scene, "flver_node_export_roll_axis")
        layout.prop(scene, "flver_node_export_mark_root_as_mesh")

    def execute(self, context):
        scene = context.scene
        armature_obj = find_armature(context)
        try:
            nodes = writer.build_nodes(
                armature_obj,
                length_axis=scene.flver_node_export_length_axis,
                roll_axis=scene.flver_node_export_roll_axis,
                mark_root_as_mesh=scene.flver_node_export_mark_root_as_mesh,
            )
            writer.write_nodes(self.filepath, nodes)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        except OSError as error:
            self.report({'ERROR'}, f"Could not write the file: {error}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Exported {len(nodes)} nodes from "
                              f"'{armature_obj.name}' to {self.filepath}")
        return {'FINISHED'}


def menu_func_export(self, context):
    """Add the exporter to File > Export."""
    self.layout.operator(FLVER_NODE_EXPORT_OT_export.bl_idname,
                         text="FLVER Nodes JSON (.json)")


classes = (
    FLVER_NODE_EXPORT_OT_export,
)
