# Axis remapping settings for FBX-style coordinate transformation

class FbxExportSettings:
    """Configuration for axis remapping during bone transform export."""

    # Default values - DO NOT CHANGE without understanding the implications
    DEFAULT_PRIMARY_AXIS = 'X'
    DEFAULT_SECONDARY_AXIS = 'Y'
    DEFAULT_MIRROR_TERTIARY = False

    def __init__(self):
        self.primary_axis = self.DEFAULT_PRIMARY_AXIS
        self.secondary_axis = self.DEFAULT_SECONDARY_AXIS
        self.mirror_tertiary_axis = self.DEFAULT_MIRROR_TERTIARY

    @classmethod
    def from_scene(cls, scene) -> 'FbxExportSettings':
        """Create settings instance from Blender scene properties."""
        settings = cls()
        settings.primary_axis = scene.armature2json_primary_axis
        settings.secondary_axis = scene.armature2json_secondary_axis
        settings.mirror_tertiary_axis = scene.armature2json_mirror_tertiary
        return settings
