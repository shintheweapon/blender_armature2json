# The Mark Root as Mesh Node choice, kept as an add-on preference so Blender
# remembers it between sessions (when it saves its preferences)

from typing import Optional

import bpy
from bpy.props import BoolProperty

# Used when the add-on has no preferences entry (for example in tests)
DEFAULT_MARK_ROOT_AS_MESH = True


class ARMATURE2JSON_preferences(bpy.types.AddonPreferences):
    """Options of the Armature2JSON add-on"""
    bl_idname = __package__

    mark_root_as_mesh: BoolProperty(
        name="Mark Root as Mesh Node",
        description="Write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone). "
                    "FLVER_Editor points every mesh it imports from FBX at node 0",
        default=DEFAULT_MARK_ROOT_AS_MESH,
    )

    def draw(self, context):
        self.layout.prop(self, "mark_root_as_mesh")


def get(context: bpy.types.Context) -> Optional[ARMATURE2JSON_preferences]:
    """
    Find the add-on's preferences.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.

    Returns
    -------
    ARMATURE2JSON_preferences or None
        The preferences, or None when the add-on has no preferences entry.
    """
    addon = context.preferences.addons.get(__package__)
    return addon.preferences if addon is not None else None


def mark_root_as_mesh(context: bpy.types.Context) -> bool:
    """
    Read the Mark Root as Mesh Node choice.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.

    Returns
    -------
    bool
        The saved choice, or the default (on) when the add-on has no
        preferences entry.
    """
    options = get(context)
    return options.mark_root_as_mesh if options is not None else DEFAULT_MARK_ROOT_AS_MESH
