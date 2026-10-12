# Armature2JSON: writes FLVER node JSON from a Blender armature

import bpy
from bpy.props import EnumProperty, StringProperty

from . import operators, prefs, ui
from .core import i18n_zh_hans, merge, transforms

_AXIS_ITEMS = [(axis, axis, f"Node {axis} axis") for axis in transforms.AXES]

# Third item of each entry is the tooltip shown in the dropdown
_MODE_ITEMS = [
    ('ARMATURE', "From Armature",
     "Build every node from the armature. No reference JSON is needed"),
    ('MERGE', "Merge into Reference JSON",
     "Keep every node of a reference JSON (for example a vanilla one from FLVER_Editor) "
     "and add the armature's bones that it lacks"),
]

_REPARENT_ITEMS = [
    (merge.KEEP_INPUT, "Keep Reference Parent",
     "Keep the reference JSON's parent and values. The bone stays where it was"),
    (merge.BLENDER_KEEP_PLACEMENT, "Use Blender Parent, Keep Placement",
     "Use the Blender parent and recompute the bone's values, so it stays where it "
     "was, axes included"),
    (merge.BLENDER_AS_IS, "Use Blender Parent, Keep Values (Armature2JSON)",
     "Use the Blender parent but keep the values relative to the old parent, "
     "as the old Armature2JSON add-on did. The bone can move"),
]

classes = (
    prefs.ARMATURE2JSON_preferences,
    *operators.classes,
    *ui.classes,
)


def register_properties():
    """Register the Scene properties that hold the export options."""
    bpy.types.Scene.armature2json_mode = EnumProperty(
        name="Mode",
        description="How to build the node list",
        items=_MODE_ITEMS,
        default='ARMATURE',
    )
    bpy.types.Scene.armature2json_input_path = StringProperty(
        name="Reference JSON",
        description="The node JSON used as the reference, usually a vanilla one exported "
                    "by FLVER_Editor. Its nodes are kept as they are",
        subtype='FILE_PATH',
        default="",
    )
    bpy.types.Scene.armature2json_reparent = EnumProperty(
        name="Reparented Bones",
        description="What to do with bones that are in the reference JSON but have a "
                    "different parent in Blender (the bone's parent in Blender is not "
                    "the parent recorded in the reference JSON)",
        items=_REPARENT_ITEMS,
        default=merge.KEEP_INPUT,
    )
    bpy.types.Scene.armature2json_length_axis = EnumProperty(
        name="Length Axis",
        description="Node axis that runs along each bone. Vanilla skeletons use the X axis",
        items=_AXIS_ITEMS,
        default=transforms.DEFAULT_LENGTH_AXIS,
    )
    bpy.types.Scene.armature2json_roll_axis = EnumProperty(
        name="Roll Axis",
        description="Node axis that each bone's Z axis becomes. "
                    "-Z gives core vanilla bones their vanilla axes",
        items=_AXIS_ITEMS,
        default=transforms.DEFAULT_ROLL_AXIS,
    )


def unregister_properties():
    """Remove the Scene properties added by :func:`register_properties`."""
    del bpy.types.Scene.armature2json_mode
    del bpy.types.Scene.armature2json_input_path
    del bpy.types.Scene.armature2json_reparent
    del bpy.types.Scene.armature2json_length_axis
    del bpy.types.Scene.armature2json_roll_axis


def register():
    """Register the extension's classes, properties, menu entry and translations."""
    bpy.app.translations.register(__name__, {'zh_HANS': i18n_zh_hans.table()})
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
    bpy.app.translations.unregister(__name__)
