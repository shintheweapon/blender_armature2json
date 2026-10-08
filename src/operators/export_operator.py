# Operator that exports the FLVER node JSON

import json
from typing import Optional

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from ..core import writer

# Names shown in a report message before the rest go to the system console
REPORT_NAMES = 5


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


def draw_options(layout: bpy.types.UILayout, scene: bpy.types.Scene) -> None:
    """
    Draw the export options, shared by the sidebar panel and the export dialog.

    Parameters
    ----------
    layout : bpy.types.UILayout
        Layout to draw into.
    scene : bpy.types.Scene
        Scene that holds the options.
    """
    layout.row().prop(scene, "flver_node_export_mode", expand=True)
    merging = scene.flver_node_export_mode == 'MERGE'
    if merging:
        col = layout.column(align=True)
        col.prop(scene, "flver_node_export_input_path")
        col.prop(scene, "flver_node_export_reparent")
    col = layout.column(align=True)
    col.prop(scene, "flver_node_export_length_axis")
    col.prop(scene, "flver_node_export_roll_axis")
    if not merging:
        layout.prop(scene, "flver_node_export_mark_root_as_mesh")


def _names(label: str, names) -> str:
    """
    Format a list of node names for a report, printing all of them.

    Parameters
    ----------
    label : str
        What the names are, for example "input nodes with no bone".
    names : list of str
        Node names.

    Returns
    -------
    str
        ``"<count> <label>: a, b, c, ..."`` with at most ``REPORT_NAMES``
        names; the full list is printed to the system console.
    """
    print(f"FLVER node export, {len(names)} {label}: {', '.join(names)}")
    shown = ', '.join(names[:REPORT_NAMES])
    more = ", ... (full list in the system console)" if len(names) > REPORT_NAMES else ""
    return f"{len(names)} {label}: {shown}{more}"


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
        draw_options(self.layout, context.scene)

    def execute(self, context):
        scene = context.scene
        armature_obj = find_armature(context)
        if scene.flver_node_export_mode == 'MERGE':
            return self._merge(scene, armature_obj)
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

    def _merge(self, scene, armature_obj):
        """Run the Merge into Input JSON mode; see :func:`writer.merge_nodes`."""
        if not scene.flver_node_export_input_path:
            self.report({'ERROR'}, "Choose an input JSON to merge into.")
            return {'CANCELLED'}
        input_path = bpy.path.abspath(scene.flver_node_export_input_path)
        try:
            with open(input_path, encoding='utf-8-sig') as handle:
                input_nodes = json.load(handle)
        except OSError as error:
            self.report({'ERROR'}, f"Could not read the input JSON: {error}")
            return {'CANCELLED'}
        except json.JSONDecodeError as error:
            self.report({'ERROR'}, f"The input JSON is not valid JSON: {error}")
            return {'CANCELLED'}
        try:
            nodes, plan = writer.merge_nodes(
                armature_obj, input_nodes,
                length_axis=scene.flver_node_export_length_axis,
                roll_axis=scene.flver_node_export_roll_axis,
                reparent=scene.flver_node_export_reparent,
            )
            writer.write_nodes(self.filepath, nodes)
        except ValueError as error:
            self.report({'ERROR'}, str(error))
            return {'CANCELLED'}
        except OSError as error:
            self.report({'ERROR'}, f"Could not write the file: {error}")
            return {'CANCELLED'}
        if plan.input_only:
            self.report({'WARNING'}, _names("input nodes with no bone, kept as they are",
                                            plan.input_only))
        if plan.reparented:
            self.report({'WARNING'}, _names("bones with another parent in Blender",
                                            plan.reparented))
        self.report({'INFO'}, f"Merged {len(plan.added)} bones from "
                              f"'{armature_obj.name}' into {len(input_nodes)} input nodes "
                              f"(inserted at {plan.insertion}); wrote {len(nodes)} nodes "
                              f"to {self.filepath}")
        return {'FINISHED'}


def menu_func_export(self, context):
    """Add the exporter to File > Export."""
    self.layout.operator(FLVER_NODE_EXPORT_OT_export.bl_idname,
                         text="FLVER Nodes JSON (.json)")


classes = (
    FLVER_NODE_EXPORT_OT_export,
)
