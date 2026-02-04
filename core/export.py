# Core export algorithm for merging Blender armature data with reference JSON

import bpy
import json
from typing import Dict, List, Optional

from .settings import FbxExportSettings
from .math_utils import matrix_to_euler_yzx, create_remap_matrix, vec_to_xyz_dict


def find_armature_root() -> Optional[bpy.types.Object]:
    """
    Find the armature object in the current scene.

    Returns:
        The active armature if selected, otherwise the first armature found,
        or None if no armature exists in the scene.
    """
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']
    if not armatures:
        return None
    # prefer active armature or first found
    if bpy.context.object and bpy.context.object.type == 'ARMATURE':
        return bpy.context.object
    return armatures[0]


def load_existing_bones(filepath: str) -> List[Dict]:
    """
    Load bone data from an existing JSON file.

    Args:
        filepath: Path to the reference JSON file (from Flver Editor)

    Returns:
        List of bone dictionaries, or empty list if file doesn't exist or is invalid

    Raises:
        FileNotFoundError: If the file doesn't exist (for UI error handling)
        json.JSONDecodeError: If the file contains invalid JSON
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        else:
            raise ValueError("JSON root is not a list. Expected a list of bone dictionaries.")


def save_bones(filepath: str, bones: List[Dict]) -> None:
    """
    Save bone data to a JSON file.

    Args:
        filepath: Output path for the JSON file
        bones: List of bone dictionaries to save
    """
    with open(filepath, 'w') as f:
        json.dump(bones, f, indent=2)


def build_missing_bones_from_blender(arm_obj: bpy.types.Object,
                                     existing_names: set,
                                     settings: FbxExportSettings) -> List[Dict]:
    """
    Build bone dictionaries for Blender bones not present in the reference JSON.

    Args:
        arm_obj: The Blender armature object
        existing_names: Set of bone names already in the reference JSON
        settings: FbxExportSettings for axis configuration

    Returns:
        List of bone dictionaries for bones found in Blender but not in reference
    """
    arm = arm_obj.data
    remap = create_remap_matrix(settings)
    inv_remap = remap.inverted()

    missing = []

    # iterate over all bones in Blender armature data
    for bone in arm.bones:
        if bone.name in existing_names:
            continue

        # compute local transform relative to parent (matrix_local already in armature space)
        if bone.parent:
            local_matrix = bone.parent.matrix_local.inverted() @ bone.matrix_local
        else:
            local_matrix = bone.matrix_local.copy()

        flver_matrix = remap @ local_matrix @ inv_remap

        rotation = matrix_to_euler_yzx(flver_matrix.to_3x3())
        translation = flver_matrix.to_translation()
        scale = flver_matrix.to_scale()

        bone_dict = {
            'Name': bone.name,
            # ParentIndex will be fixed later when we know final list ordering
            'ParentIndex': -1,
            'FirstChildIndex': -1,
            'NextSiblingIndex': -1,
            'PreviousSiblingIndex': -1,
            'Translation': vec_to_xyz_dict(translation),
            'Rotation': vec_to_xyz_dict(rotation),
            'Scale': vec_to_xyz_dict(scale),
            'BoundingBoxMin': {'X': 0.0, 'Y': 0.0, 'Z': 0.0},
            'BoundingBoxMax': {'X': 0.0, 'Y': 0.0, 'Z': 0.0},
            'Flags': 8  # Default flag for new bones
        }

        missing.append(bone_dict)

    return missing


def get_flags_group_order(flags: int) -> int:
    """
    Get the sorting order for bones based on their Flags value.

    The pattern is: 10s/8s first, then 4s, then 2s, then 1s, then others.

    Args:
        flags: The Flags value from a bone dictionary

    Returns:
        Integer representing sort priority (lower = earlier in list)
    """
    if flags == 10 or flags == 8:
        return 1  # First group
    elif flags == 4:
        return 2  # Second group
    elif flags == 2:
        return 3  # Third group
    elif flags == 1:
        return 4  # Fourth group
    else:
        # For other flag values, sort them by value but after known groups
        return 5


def find_insertion_point(existing_bones: List[Dict]) -> int:
    """
    Find the position to insert new bones after the last bone with Flags=8 or 10.

    Args:
        existing_bones: List of bone dictionaries from reference JSON

    Returns:
        Index where new bones should be inserted
    """
    last_8_or_10_index = -1

    for i, bone in enumerate(existing_bones):
        flags = bone.get('Flags', 1)
        if flags == 8 or flags == 10:
            last_8_or_10_index = i

    # Insert after the last 8/10 bone
    return last_8_or_10_index + 1 if last_8_or_10_index != -1 else 0


def merge_bones_with_correct_order(xml_bones: List[Dict], missing_bones: List[Dict]) -> List[Dict]:
    """
    Merge existing reference bones with new Blender bones.

    New bones are inserted after the last bone with Flags=8 or 10.

    Args:
        xml_bones: Bone dictionaries from reference JSON
        missing_bones: Bone dictionaries for bones only in Blender

    Returns:
        Merged list of bone dictionaries
    """
    if not missing_bones:
        return xml_bones

    insertion_point = find_insertion_point(xml_bones)

    # Insert missing bones at the correct position
    merged_bones = xml_bones[:insertion_point] + missing_bones + xml_bones[insertion_point:]

    return merged_bones


def recompute_hierarchy_indices(final_bones: List[Dict], arm: bpy.types.Armature) -> None:
    """
    Recompute hierarchy indices for the final bone list.

    Updates ParentIndex, FirstChildIndex, NextSiblingIndex, and PreviousSiblingIndex
    based on bone names and the Blender armature structure.

    Args:
        final_bones: List of bone dictionaries to update (modified in place)
        arm: Blender Armature data containing hierarchy information

    Notes:
        - Bones that exist in final_bones but not in the armature keep their original indices
        - Bones that exist in the armature but not in final_bones are ignored
    """
    name_to_index = {b['Name']: i for i, b in enumerate(final_bones)}

    # Set ParentIndex based on armature hierarchy where possible
    for arm_bone in arm.bones:
        name = arm_bone.name
        if name not in name_to_index:
            continue
        idx = name_to_index[name]
        parent_idx = -1
        if arm_bone.parent and arm_bone.parent.name in name_to_index:
            parent_idx = name_to_index[arm_bone.parent.name]
        final_bones[idx]['ParentIndex'] = parent_idx

    # FirstChildIndex
    for arm_bone in arm.bones:
        if arm_bone.children:
            parent_name = arm_bone.name
            if parent_name in name_to_index:
                parent_idx = name_to_index[parent_name]
                # find first child in the child's order that's in final_bones
                first_child_idx = -1
                for child in arm_bone.children:
                    if child.name in name_to_index:
                        first_child_idx = name_to_index[child.name]
                        break
                final_bones[parent_idx]['FirstChildIndex'] = first_child_idx

    # Sibling indices (Previous/Next)
    for arm_bone in arm.bones:
        if arm_bone.parent:
            siblings = arm_bone.parent.children
        else:
            # top-level bones: siblings are other top-levels
            siblings = [b for b in arm.bones if b.parent is None]

        # process siblings order
        for i, sb in enumerate(siblings):
            if sb.name not in name_to_index:
                continue
            idx = name_to_index[sb.name]
            # previous sibling
            prev_idx = -1
            if i > 0 and siblings[i-1].name in name_to_index:
                prev_idx = name_to_index[siblings[i-1].name]
            # next sibling
            next_idx = -1
            if i < len(siblings)-1 and siblings[i+1].name in name_to_index:
                next_idx = name_to_index[siblings[i+1].name]

            final_bones[idx]['PreviousSiblingIndex'] = prev_idx
            final_bones[idx]['NextSiblingIndex'] = next_idx

    # For any bones that exist in final_bones but are not present in the armature,
    # keep whatever ParentIndex was already in the JSON.


def export_using_json_as_source(input_filepath: str,
                                 output_filepath: str,
                                 settings: FbxExportSettings) -> dict:
    """
    Main export function that merges Blender armature data with reference JSON.

    Args:
        input_filepath: Path to reference JSON from Flver Editor
        output_filepath: Path where merged JSON will be saved
        settings: FbxExportSettings for axis configuration

    Returns:
        Dictionary with export statistics:
        - 'reference_count': Number of bones in reference JSON
        - 'added_count': Number of bones added from Blender
        - 'total_count': Total bones in output
        - 'insertion_point': Index where new bones were inserted

    Raises:
        Exception: If no armature found in scene
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If input file contains invalid JSON
        ValueError: If JSON structure is invalid
    """
    arm_obj = find_armature_root()
    if not arm_obj or arm_obj.type != 'ARMATURE':
        raise Exception("No armature found in the scene. Please add an armature or select one.")

    arm = arm_obj.data

    # 1) Load bones from reference JSON
    xml_bones = load_existing_bones(input_filepath)
    xml_names = {b['Name'] for b in xml_bones}

    # 2) Find missing bones present in Blender but not in reference
    missing_bones = build_missing_bones_from_blender(arm_obj, xml_names, settings)

    # 3) Merge with correct ordering
    final_bones = merge_bones_with_correct_order(xml_bones, missing_bones)

    # 4) Recompute hierarchy indices
    recompute_hierarchy_indices(final_bones, arm)

    # 5) Save to output path
    save_bones(output_filepath, final_bones)

    return {
        'reference_count': len(xml_bones),
        'added_count': len(missing_bones),
        'total_count': len(final_bones),
        'insertion_point': find_insertion_point(xml_bones),
    }
