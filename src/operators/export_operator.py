# Operator that exports the FLVER node JSON

import json
from typing import Optional

import bpy
from bpy.props import StringProperty
from bpy_extras.io_utils import ExportHelper

from .. import prefs
from ..core import files, messages, transforms, writer

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


def draw_options(layout: bpy.types.UILayout, context: bpy.types.Context) -> None:
    """
    Draw the export options, shared by the sidebar panel and the export dialog.

    Parameters
    ----------
    layout : bpy.types.UILayout
        Layout to draw into.
    context : bpy.types.Context
        Current Blender context: its scene holds most options, the add-on
        preferences hold Mark Root as Mesh Node.
    """
    scene = context.scene
    layout.row().prop(scene, "armature2json_mode", expand=True)
    merging = scene.armature2json_mode == 'MERGE'
    if merging:
        col = layout.column(align=True)
        col.prop(scene, "armature2json_input_path")
        col.prop(scene, "armature2json_reparent")
    layout.prop(scene, "armature2json_space")
    col = layout.column(align=True)
    col.prop(scene, "armature2json_length_axis")
    col.prop(scene, "armature2json_roll_axis")
    row = col.row(align=True)
    row.operator(ARMATURE2JSON_OT_reset_axes.bl_idname, icon='LOOP_BACK')
    row.operator(ARMATURE2JSON_OT_axes_as_imported.bl_idname)
    options = prefs.get(context)
    if not merging and options is not None:
        layout.prop(options, "mark_root_as_mesh")


def _text(template: str, **fields) -> str:
    """
    Fill a message template from :mod:`core.messages`, in the interface
    language when Blender translates reports.

    Parameters
    ----------
    template : str
        One of the templates in :mod:`core.messages`.
    **fields
        Values for its named fields.

    Returns
    -------
    str
        The message.
    """
    return bpy.app.translations.pgettext_rpt(template).format(**fields)


def _names(template: str, names) -> str:
    """
    Format a list of node names for a report, printing all of them.

    Parameters
    ----------
    template : str
        ``messages.REFERENCE_ONLY`` or ``messages.REPARENTED``, with the
        fields ``count`` and ``names``.
    names : list of str
        Node names.

    Returns
    -------
    str
        The message with at most ``REPORT_NAMES`` names; the full list is
        printed to the system console.
    """
    print("FLVER node export: " + template.format(count=len(names), names=', '.join(names)))
    shown = ', '.join(names[:REPORT_NAMES])
    if len(names) > REPORT_NAMES:
        shown += _text(messages.MORE_IN_CONSOLE)
    return _text(template, count=len(names), names=shown)


def _error_text(error: ValueError) -> str:
    """
    Turn an export error into a report message.

    Parameters
    ----------
    error : ValueError
        An :class:`core.messages.ExportError`, or any other ``ValueError``.

    Returns
    -------
    str
        The message from the error's template, or ``str(error)``.
    """
    if isinstance(error, messages.ExportError):
        return _text(error.template, **error.fields)
    return str(error)


class ARMATURE2JSON_OT_export(bpy.types.Operator, ExportHelper):
    """Export the armature's bones as a FLVER node JSON for FLVER_Editor"""
    bl_idname = "armature2json.export"
    bl_label = "Export FLVER Nodes JSON"
    bl_options = {'REGISTER'}

    filename_ext = ".json"
    filter_glob: StringProperty(default="*.json", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return find_armature(context) is not None

    def draw(self, context):
        draw_options(self.layout, context)

    def execute(self, context):
        scene = context.scene
        armature_obj = find_armature(context)
        if scene.armature2json_mode == 'MERGE':
            return self._merge(scene, armature_obj)
        try:
            nodes = writer.build_nodes(
                armature_obj,
                length_axis=scene.armature2json_length_axis,
                roll_axis=scene.armature2json_roll_axis,
                mark_root_as_mesh=prefs.mark_root_as_mesh(context),
                space=scene.armature2json_space,
            )
            writer.write_nodes(self.filepath, nodes)
        except ValueError as error:
            self.report({'ERROR'}, _error_text(error))
            return {'CANCELLED'}
        except OSError as error:
            self.report({'ERROR'}, _text(messages.CANNOT_WRITE, error=error))
            return {'CANCELLED'}
        self.report({'INFO'}, _text(messages.EXPORTED, count=len(nodes),
                                    armature=armature_obj.name, path=self.filepath))
        return {'FINISHED'}

    def _merge(self, scene, armature_obj):
        """Run the Merge into Reference JSON mode; see :func:`writer.merge_nodes`."""
        if not scene.armature2json_input_path:
            self.report({'ERROR'}, _text(messages.CHOOSE_REFERENCE))
            return {'CANCELLED'}
        input_path = bpy.path.abspath(scene.armature2json_input_path)
        if files.same_file(self.filepath, input_path):
            self.report({'ERROR'}, _text(messages.WOULD_OVERWRITE))
            return {'CANCELLED'}
        try:
            with open(input_path, encoding='utf-8-sig') as handle:
                input_nodes = json.load(handle)
        except OSError as error:
            self.report({'ERROR'}, _text(messages.CANNOT_READ, error=error))
            return {'CANCELLED'}
        except json.JSONDecodeError as error:
            self.report({'ERROR'}, _text(messages.NOT_JSON, error=error))
            return {'CANCELLED'}
        try:
            nodes, plan = writer.merge_nodes(
                armature_obj, input_nodes,
                length_axis=scene.armature2json_length_axis,
                roll_axis=scene.armature2json_roll_axis,
                reparent=scene.armature2json_reparent,
                space=scene.armature2json_space,
            )
            writer.write_nodes(self.filepath, nodes)
        except ValueError as error:
            self.report({'ERROR'}, _error_text(error))
            return {'CANCELLED'}
        except OSError as error:
            self.report({'ERROR'}, _text(messages.CANNOT_WRITE, error=error))
            return {'CANCELLED'}
        if plan.input_only:
            self.report({'WARNING'}, _names(messages.REFERENCE_ONLY, plan.input_only))
        if plan.reparented:
            self.report({'WARNING'}, _names(messages.REPARENTED, plan.reparented))
        self.report({'INFO'}, _text(messages.MERGED, added=len(plan.added),
                                    armature=armature_obj.name, inputs=len(input_nodes),
                                    insertion=plan.insertion, count=len(nodes),
                                    path=self.filepath))
        return {'FINISHED'}


class ARMATURE2JSON_OT_reset_axes(bpy.types.Operator):
    """Length X, Roll -Z (default). In game, each bone gets vanilla-style axes worked out from its Blender direction. Can disagree with a custom Havok skeleton"""
    bl_idname = "armature2json.reset_axes"
    bl_label = "Reset Axes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.armature2json_length_axis = transforms.DEFAULT_LENGTH_AXIS
        scene.armature2json_roll_axis = transforms.DEFAULT_ROLL_AXIS
        return {'FINISHED'}


class ARMATURE2JSON_OT_axes_as_imported(bpy.types.Operator):
    """Length Y, Roll Z. In game, each bone keeps exactly its Blender axes, the same axes a custom Havok skeleton gets. Use after Match Vanilla Orientations"""
    bl_idname = "armature2json.axes_as_imported"
    bl_label = "As Imported"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.armature2json_length_axis = 'Y'
        scene.armature2json_roll_axis = 'Z'
        return {'FINISHED'}


def menu_func_export(self, context):
    """Add the exporter to File > Export."""
    self.layout.operator(ARMATURE2JSON_OT_export.bl_idname,
                         text="FLVER Nodes JSON (.json)")


classes = (
    ARMATURE2JSON_OT_export,
    ARMATURE2JSON_OT_reset_axes,
    ARMATURE2JSON_OT_axes_as_imported,
)
