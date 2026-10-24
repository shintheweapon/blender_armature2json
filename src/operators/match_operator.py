# Operator that turns the armature's vanilla-named bones to the vanilla axes

import json

import bpy

from .. import prefs
from ..core import messages, orientations, transforms
from .export_operator import _error_text, _text, find_armature


class ARMATURE2JSON_OT_match_vanilla(bpy.types.Operator):
    """Turn the bones that have vanilla names to the vanilla skeleton's axes, keeping each bone's head and length; other bones stay as they are. Uses the Coordinate Space and axes below. Do it before exporting the FBX for Havok, so the physics skeleton gets the same axes. Ctrl+Z undoes it"""
    bl_idname = "armature2json.match_vanilla"
    bl_label = "Match Vanilla Orientations"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        armature_obj = find_armature(context)
        if armature_obj is None:
            self.report({'ERROR'}, _text(messages.NO_ARMATURE))
            return {'CANCELLED'}
        path = prefs.vanilla_reference_path(context)
        if not path:
            self.report({'ERROR'}, _text(messages.CHOOSE_VANILLA_REFERENCE))
            return {'CANCELLED'}
        try:
            reference = orientations.load_reference(bpy.path.abspath(path))
            space = transforms.space_mapping(scene.armature2json_space,
                                             armature_obj.matrix_world)
            axes = transforms.axis_matrix(scene.armature2json_length_axis,
                                          scene.armature2json_roll_axis)
        except OSError as error:
            self.report({'ERROR'}, _text(messages.CANNOT_READ, error=error))
            return {'CANCELLED'}
        except json.JSONDecodeError as error:
            self.report({'ERROR'}, _text(messages.NOT_JSON, error=error))
            return {'CANCELLED'}
        except (KeyError, TypeError):
            self.report({'ERROR'}, _text(messages.NOT_A_LIST))
            return {'CANCELLED'}
        except ValueError as error:
            self.report({'ERROR'}, _error_text(error))
            return {'CANCELLED'}
        matched = orientations.match_orientations(armature_obj, reference, space, axes)
        self.report({'INFO'}, _text(messages.MATCHED, count=len(matched),
                                    total=len(armature_obj.data.bones),
                                    armature=armature_obj.name))
        return {'FINISHED'}


classes = (
    ARMATURE2JSON_OT_match_vanilla,
)
