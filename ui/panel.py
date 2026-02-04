# UI panels for armature to JSON export

import bpy
import os


class ARMATURE2JSON_PT_main_panel(bpy.types.Panel):
    """Main panel for Armature to JSON export"""
    bl_label = "Armature to JSON"
    bl_idname = "ARMATURE2JSON_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature2JSON"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # === Input File Section ===
        box = layout.box()
        row = box.row()
        row.label(text="Reference JSON (Required)", icon='FILE')

        # Input file path display and selector
        row = box.row(align=True)
        input_path = scene.armature2json_input_path
        if input_path:
            display_name = os.path.basename(input_path)
            row.label(text=display_name, icon='CHECKMARK')
        else:
            row.label(text="No file selected", icon='ERROR')
        row.operator("armature2json.select_input", text="", icon='FILE_FOLDER')

        # Show full path on a smaller row
        if input_path:
            sub = box.row()
            sub.scale_y = 0.6
            # Truncate long paths
            display_path = input_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            sub.label(text=display_path)

        # Tooltip/help text for reference JSON
        help_box = box.box()
        help_box.scale_y = 0.7
        col = help_box.column(align=True)
        col.label(text="Get this file by exporting from Flver Editor", icon='INFO')

        layout.separator()

        # === Output File Section ===
        box = layout.box()
        row = box.row()
        row.label(text="Output JSON", icon='EXPORT')

        row = box.row(align=True)
        output_path = scene.armature2json_output_path
        if output_path:
            display_name = os.path.basename(output_path)
            row.label(text=display_name, icon='CHECKMARK')
        else:
            row.label(text="No location selected", icon='ERROR')
        row.operator("armature2json.select_output", text="", icon='FILE_FOLDER')

        if output_path:
            sub = box.row()
            sub.scale_y = 0.6
            display_path = output_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            sub.label(text=display_path)

        layout.separator()

        # === Export Button ===
        row = layout.row(align=True)
        row.scale_y = 1.5

        # Check prerequisites for enabling export
        has_armature = any(obj.type == 'ARMATURE' for obj in context.scene.objects)
        can_export = input_path and output_path and has_armature

        if can_export:
            row.operator("armature2json.export", text="Export", icon='EXPORT')
        else:
            row.enabled = False
            row.operator("armature2json.export", text="Export", icon='EXPORT')

        # === Validation Messages ===
        if not has_armature:
            box = layout.box()
            box.alert = True
            box.label(text="No armature in scene!", icon='ERROR')
        elif not input_path:
            box = layout.box()
            box.alert = True
            box.label(text="Select a reference JSON file", icon='ERROR')
        elif not output_path:
            box = layout.box()
            box.alert = True
            box.label(text="Select an output location", icon='ERROR')


class ARMATURE2JSON_PT_axis_settings(bpy.types.Panel):
    """Axis settings sub-panel"""
    bl_label = "Axis Settings"
    bl_idname = "ARMATURE2JSON_PT_axis_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature2JSON"
    bl_parent_id = "ARMATURE2JSON_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Warning message
        warn_box = layout.box()
        warn_box.alert = True
        col = warn_box.column(align=True)
        col.scale_y = 0.8
        col.label(text="Changing these settings may cause", icon='ERROR')
        col.label(text="unexpected results in the output!")

        layout.separator()

        # Axis settings
        col = layout.column(align=True)
        col.prop(scene, "armature2json_primary_axis", text="Primary Axis")
        col.prop(scene, "armature2json_secondary_axis", text="Secondary Axis")
        col.prop(scene, "armature2json_mirror_tertiary", text="Mirror Tertiary Axis")

        layout.separator()

        # Reset button
        row = layout.row()
        row.operator("armature2json.reset_axis_settings", text="Reset to Defaults", icon='LOOP_BACK')


class ARMATURE2JSON_PT_info_panel(bpy.types.Panel):
    """Information and help panel"""
    bl_label = "Help"
    bl_idname = "ARMATURE2JSON_PT_info"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Armature2JSON"
    bl_parent_id = "ARMATURE2JSON_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout

        layout.label(text="Workflow:", icon='QUESTION')
        col = layout.column(align=True)
        col.scale_y = 0.8
        col.label(text="1. Export skeleton JSON from Flver Editor")
        col.label(text="2. Import your armature into Blender")
        col.label(text="3. Select the Flver Editor JSON as Reference")
        col.label(text="4. Choose where to save the output")
        col.label(text="5. Click Export")

        layout.separator()

        layout.label(text="What this does:", icon='INFO')
        col = layout.column(align=True)
        col.scale_y = 0.8
        col.label(text="Merges bones from your Blender armature")
        col.label(text="with the reference JSON, preserving")
        col.label(text="existing bone data and adding new bones.")


# List of classes to register
classes = (
    ARMATURE2JSON_PT_main_panel,
    ARMATURE2JSON_PT_axis_settings,
    ARMATURE2JSON_PT_info_panel,
)
