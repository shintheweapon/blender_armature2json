# The Mark Root as Mesh Node and Vanilla Bone Orientations choices, kept as
# add-on preferences so Blender remembers them between sessions (when it saves
# its preferences)

from typing import Optional

import bpy
from bpy.props import BoolProperty, StringProperty

# Used when the add-on has no preferences entry (for example in tests)
DEFAULT_MARK_ROOT_AS_MESH = True
DEFAULT_VANILLA_ORIENTATIONS = True


class ARMATURE2JSON_preferences(bpy.types.AddonPreferences):
    """Options of the Armature2JSON add-on"""
    bl_idname = __package__

    mark_root_as_mesh: BoolProperty(
        name="Mark Root as Mesh Node",
        description="Write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone). "
                    "FLVER_Editor points every mesh it imports from FBX at node 0",
        default=DEFAULT_MARK_ROOT_AS_MESH,
    )
    vanilla_orientations: BoolProperty(
        name="Vanilla Bone Orientations",
        description="Give bones with Elden Ring bone names their vanilla orientation, keeping "
                    "their positions. Without ERCS, the game turns the mesh around any bone "
                    "whose orientation differs from vanilla",
        default=DEFAULT_VANILLA_ORIENTATIONS,
    )
    vanilla_reference_path: StringProperty(
        name="Vanilla Reference JSON",
        description="Node JSON of the vanilla character skeleton, whose axes the game's "
                    "animations use: export it from chr\\c0000-chrbnd-dcx\\c0000.flver with "
                    "FLVER Editor (Nodes.json). Remembered between sessions",
        subtype='FILE_PATH',
        default="",
    )

    def draw(self, context):
        self.layout.prop(self, "vanilla_reference_path")
        self.layout.prop(self, "mark_root_as_mesh")
        self.layout.prop(self, "vanilla_orientations")


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


def vanilla_orientations(context: bpy.types.Context) -> bool:
    """
    Read the Vanilla Bone Orientations choice.

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
    return options.vanilla_orientations if options is not None else DEFAULT_VANILLA_ORIENTATIONS


def vanilla_reference_path(context: bpy.types.Context) -> str:
    """
    Read the remembered Vanilla Reference JSON path.

    Parameters
    ----------
    context : bpy.types.Context
        Current Blender context.

    Returns
    -------
    str
        The saved path, or an empty string when none is set or the add-on
        has no preferences entry.
    """
    options = get(context)
    return options.vanilla_reference_path if options is not None else ""
