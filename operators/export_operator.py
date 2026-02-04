# Operators for armature to JSON export

import bpy
import os
import json
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper


class ARMATURE2JSON_OT_select_input(bpy.types.Operator, ImportHelper):
    """Select the reference JSON file exported from Flver Editor"""
    bl_idname = "armature2json.select_input"
    bl_label = "Select Reference JSON"
    bl_options = {'REGISTER', 'UNDO'}

    # File browser filter
    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    filename_ext = ".json"

    def execute(self, context):
        # Store the selected path in scene properties
        context.scene.armature2json_input_path = self.filepath

        # Auto-suggest output filename if not already set
        if not context.scene.armature2json_output_path:
            input_dir = os.path.dirname(self.filepath)
            input_name = os.path.splitext(os.path.basename(self.filepath))[0]
            suggested_output = os.path.join(input_dir, f"{input_name}_merged.json")
            context.scene.armature2json_output_path = suggested_output

        self.report({'INFO'}, f"Reference JSON selected: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class ARMATURE2JSON_OT_select_output(bpy.types.Operator, ExportHelper):
    """Select the output location for the merged JSON file"""
    bl_idname = "armature2json.select_output"
    bl_label = "Select Output Location"
    bl_options = {'REGISTER', 'UNDO'}

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
    )

    filename_ext = ".json"

    # Suggest a default filename
    filename: StringProperty(
        default="armature_export.json",
    )

    def invoke(self, context, event):
        # Pre-fill with suggested name if input is set
        if context.scene.armature2json_input_path:
            input_name = os.path.splitext(os.path.basename(context.scene.armature2json_input_path))[0]
            self.filename = f"{input_name}_merged.json"
        return super().invoke(context, event)

    def execute(self, context):
        context.scene.armature2json_output_path = self.filepath
        self.report({'INFO'}, f"Output location set: {os.path.basename(self.filepath)}")
        return {'FINISHED'}


class ARMATURE2JSON_OT_export(bpy.types.Operator):
    """Export armature data merged with reference JSON"""
    bl_idname = "armature2json.export"
    bl_label = "Export Armature JSON"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """Check if export can proceed."""
        scene = context.scene
        has_input = bool(scene.armature2json_input_path)
        has_output = bool(scene.armature2json_output_path)
        has_armature = any(obj.type == 'ARMATURE' for obj in context.scene.objects)
        return has_input and has_output and has_armature

    def execute(self, context):
        from ..core import export_using_json_as_source, FbxExportSettings

        scene = context.scene
        input_path = scene.armature2json_input_path
        output_path = scene.armature2json_output_path

        # Validate input file exists
        if not os.path.isfile(input_path):
            self.report({'ERROR'}, f"Reference JSON file not found: {input_path}")
            return {'CANCELLED'}

        try:
            # Create settings from scene properties
            settings = FbxExportSettings.from_scene(scene)

            # Run the export
            result = export_using_json_as_source(input_path, output_path, settings)

            # Report success
            self.report(
                {'INFO'},
                f"Export complete! Reference: {result['reference_count']} bones, "
                f"Added: {result['added_count']}, Total: {result['total_count']}"
            )
            return {'FINISHED'}

        except FileNotFoundError as e:
            self.report({'ERROR'}, f"File not found: {e}")
            return {'CANCELLED'}
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"Invalid JSON file: {e}")
            return {'CANCELLED'}
        except ValueError as e:
            self.report({'ERROR'}, f"Invalid JSON structure: {e}")
            return {'CANCELLED'}
        except PermissionError:
            self.report({'ERROR'}, f"Cannot write to output location. Check file permissions.")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}


class ARMATURE2JSON_OT_reset_axis_settings(bpy.types.Operator):
    """Reset axis settings to default values (X, Y, No Mirror)"""
    bl_idname = "armature2json.reset_axis_settings"
    bl_label = "Reset to Defaults"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        from ..core import FbxExportSettings

        scene = context.scene
        scene.armature2json_primary_axis = FbxExportSettings.DEFAULT_PRIMARY_AXIS
        scene.armature2json_secondary_axis = FbxExportSettings.DEFAULT_SECONDARY_AXIS
        scene.armature2json_mirror_tertiary = FbxExportSettings.DEFAULT_MIRROR_TERTIARY

        self.report({'INFO'}, "Axis settings reset to defaults")
        return {'FINISHED'}


# List of classes to register
classes = (
    ARMATURE2JSON_OT_select_input,
    ARMATURE2JSON_OT_select_output,
    ARMATURE2JSON_OT_export,
    ARMATURE2JSON_OT_reset_axis_settings,
)
