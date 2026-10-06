# FLVER Node Exporter: writes FLVER node JSON from a Blender armature

import bpy
from bpy.props import BoolProperty, EnumProperty

from . import operators, ui
from .core import transforms

_AXIS_ITEMS = [(axis, axis, f"Node {axis} axis") for axis in transforms.AXES]

classes = (
    *operators.classes,
    *ui.classes,
)


def register_properties():
    """Register the Scene properties that hold the export options."""
    bpy.types.Scene.flver_node_export_length_axis = EnumProperty(
        name="Length Axis",
        description="Node axis that runs along each bone. Vanilla skeletons use X",
        items=_AXIS_ITEMS,
        default=transforms.DEFAULT_LENGTH_AXIS,
    )
    bpy.types.Scene.flver_node_export_roll_axis = EnumProperty(
        name="Roll Axis",
        description="Node axis that each bone's Z axis becomes. "
                    "-Z gives core vanilla bones their vanilla axes",
        items=_AXIS_ITEMS,
        default=transforms.DEFAULT_ROLL_AXIS,
    )
    bpy.types.Scene.flver_node_export_mark_root_as_mesh = BoolProperty(
        name="Mark Root as Mesh Node",
        description="Write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone). "
                    "FLVER_Editor points every mesh it imports from FBX at node 0",
        default=True,
    )


def unregister_properties():
    """Remove the Scene properties added by :func:`register_properties`."""
    del bpy.types.Scene.flver_node_export_length_axis
    del bpy.types.Scene.flver_node_export_roll_axis
    del bpy.types.Scene.flver_node_export_mark_root_as_mesh


def register():
    """Register the extension's classes, properties and menu entry."""
    for cls in classes:
        bpy.utils.register_class(cls)
    register_properties()
    bpy.types.TOPBAR_MT_file_export.append(operators.menu_func_export)


def unregister():
    """Unregister everything added by :func:`register`."""
    bpy.types.TOPBAR_MT_file_export.remove(operators.menu_func_export)
    unregister_properties()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
