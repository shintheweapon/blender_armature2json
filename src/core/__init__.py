# Core module for armature to JSON export functionality

from .settings import FbxExportSettings
from .math_utils import matrix_to_euler_yzx, create_remap_matrix, vec_to_xyz_dict
from .export import (
    find_armature_root,
    load_existing_bones,
    save_bones,
    build_missing_bones_from_blender,
    get_flags_group_order,
    find_insertion_point,
    merge_bones_with_correct_order,
    recompute_hierarchy_indices,
    export_using_json_as_source,
)

__all__ = [
    'FbxExportSettings',
    'matrix_to_euler_yzx',
    'create_remap_matrix',
    'vec_to_xyz_dict',
    'find_armature_root',
    'load_existing_bones',
    'save_bones',
    'build_missing_bones_from_blender',
    'get_flags_group_order',
    'find_insertion_point',
    'merge_bones_with_correct_order',
    'recompute_hierarchy_indices',
    'export_using_json_as_source',
]
