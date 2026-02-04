# Armature to JSON Exporter - Blender Addon
# Merges Blender armature data with Flver Editor JSON export

bl_info = {
    "name": "Armature to JSON Exporter",
    "author": "blender_armature2json",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Armature2JSON",
    "description": "Merge Blender armature data with Flver Editor JSON export",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "category": "Import-Export",
}

import bpy
from bpy.props import StringProperty, EnumProperty, BoolProperty

# Import submodules
from . import operators
from . import ui


def register_properties():
    """Register scene properties for the addon."""

    bpy.types.Scene.armature2json_input_path = StringProperty(
        name="Input JSON Path",
        description="Path to the reference JSON file exported from Flver Editor. "
                    "This file contains the original bone data that will be merged "
                    "with bones from the Blender armature",
        default="",
        subtype='FILE_PATH',
    )

    bpy.types.Scene.armature2json_output_path = StringProperty(
        name="Output JSON Path",
        description="Path where the merged JSON file will be saved",
        default="",
        subtype='FILE_PATH',
    )

    bpy.types.Scene.armature2json_primary_axis = EnumProperty(
        name="Primary Axis",
        description="Primary axis for FBX-style coordinate remapping. "
                    "Default: X. Changing this may cause unexpected results",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('-X', "-X", ""),
            ('-Y', "-Y", ""),
            ('-Z', "-Z", ""),
        ],
        default='X',
    )

    bpy.types.Scene.armature2json_secondary_axis = EnumProperty(
        name="Secondary Axis",
        description="Secondary axis for FBX-style coordinate remapping. "
                    "Default: Y. Changing this may cause unexpected results",
        items=[
            ('X', "X", ""),
            ('Y', "Y", ""),
            ('Z', "Z", ""),
            ('-X', "-X", ""),
            ('-Y', "-Y", ""),
            ('-Z', "-Z", ""),
        ],
        default='Y',
    )

    bpy.types.Scene.armature2json_mirror_tertiary = BoolProperty(
        name="Mirror Tertiary Axis",
        description="Mirror the computed tertiary axis. "
                    "Default: Off. Changing this may cause unexpected results",
        default=False,
    )


def unregister_properties():
    """Unregister scene properties."""
    del bpy.types.Scene.armature2json_input_path
    del bpy.types.Scene.armature2json_output_path
    del bpy.types.Scene.armature2json_primary_axis
    del bpy.types.Scene.armature2json_secondary_axis
    del bpy.types.Scene.armature2json_mirror_tertiary


# Collect all classes for registration
classes = (
    *operators.classes,
    *ui.classes,
)


def register():
    """Register the addon."""
    # Register all classes
    for cls in classes:
        bpy.utils.register_class(cls)

    # Register properties
    register_properties()

    print("Armature2JSON addon registered")


def unregister():
    """Unregister the addon."""
    # Unregister properties first
    unregister_properties()

    # Unregister classes in reverse order
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    print("Armature2JSON addon unregistered")


if __name__ == "__main__":
    register()
