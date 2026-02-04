# Math utilities for matrix and vector operations

import mathutils
from math import atan2, asin, pi
from typing import Dict

from .settings import FbxExportSettings


def matrix_to_euler_yzx(M: mathutils.Matrix) -> mathutils.Vector:
    """
    Convert a 3x3 rotation matrix to Euler angles in YZX order.

    Args:
        M: A 3x3 rotation matrix

    Returns:
        Vector(x, y, z) containing Euler angles in radians
    """
    m11 = M[0][0]; m21 = M[1][0]; m31 = M[2][0]
    m22 = M[1][1]; m23 = M[1][2]; m32 = M[2][1]; m33 = M[2][2]

    if abs(m21) > 0.99999:
        z = pi/2.0 if m21 > 0 else -pi/2.0
        y = 0.0
        x = atan2(m32, m33)
    else:
        z = asin(m21)
        y = atan2(-m31, m11)
        x = atan2(-m23, m22)
    return mathutils.Vector((x, y, z))


def create_remap_matrix(settings: FbxExportSettings) -> mathutils.Matrix:
    """
    Create a coordinate remapping matrix based on FBX export settings.

    Args:
        settings: FbxExportSettings instance with axis configuration

    Returns:
        4x4 transformation matrix for coordinate remapping
    """
    axis_map = {
        'X': mathutils.Vector((1, 0, 0)),
        'Y': mathutils.Vector((0, 1, 0)),
        'Z': mathutils.Vector((0, 0, 1)),
        '-X': mathutils.Vector((-1, 0, 0)),
        '-Y': mathutils.Vector((0, -1, 0)),
        '-Z': mathutils.Vector((0, 0, -1))
    }
    new_x = axis_map.get(settings.primary_axis, mathutils.Vector((1, 0, 0)))
    new_y = axis_map.get(settings.secondary_axis, mathutils.Vector((0, 1, 0)))
    new_z = new_x.cross(new_y)
    if settings.mirror_tertiary_axis:
        new_z = -new_z
    remap_matrix = mathutils.Matrix((
        (new_x.x, new_y.x, new_z.x, 0),
        (new_x.y, new_y.y, new_z.y, 0),
        (new_x.z, new_y.z, new_z.z, 0),
        (0, 0, 0, 1)
    ))
    return remap_matrix


def vec_to_xyz_dict(v: mathutils.Vector) -> Dict[str, float]:
    """
    Convert a mathutils.Vector to a dictionary with X, Y, Z keys.

    Args:
        v: A 3D vector

    Returns:
        Dictionary with 'X', 'Y', 'Z' keys and float values
    """
    return {"X": float(v.x), "Y": float(v.y), "Z": float(v.z)}
