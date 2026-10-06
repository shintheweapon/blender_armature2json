# Transforms between Blender armature space and FLVER node space

import math
from typing import Optional, Tuple

from mathutils import Matrix, Vector

# Choices for the length axis and roll axis options, in display order
AXES = ('X', 'Y', 'Z', '-X', '-Y', '-Z')

DEFAULT_LENGTH_AXIS = 'X'
DEFAULT_ROLL_AXIS = '-Z'

# FLVER space is Blender space turned Y-up and mirrored along Z
Y_UP = Matrix.Rotation(-math.pi / 2.0, 4, 'X')
MIRROR_Z = Matrix.Diagonal((1.0, 1.0, -1.0, 1.0))

_AXIS_VECTORS = {
    'X': Vector((1.0, 0.0, 0.0)),
    'Y': Vector((0.0, 1.0, 0.0)),
    'Z': Vector((0.0, 0.0, 1.0)),
    '-X': Vector((-1.0, 0.0, 0.0)),
    '-Y': Vector((0.0, -1.0, 0.0)),
    '-Z': Vector((0.0, 0.0, -1.0)),
}


def axis_matrix(length_axis: str = DEFAULT_LENGTH_AXIS,
                roll_axis: str = DEFAULT_ROLL_AXIS) -> Matrix:
    """
    Build the change of axes from a Blender bone to its FLVER node.

    The bone's Y axis (along its length) becomes the node's ``length_axis``
    and the bone's Z axis becomes the node's ``roll_axis``. The remaining
    axis follows from the right-hand rule.

    Parameters
    ----------
    length_axis : str
        Node axis that runs along the bone, one of ``AXES``.
    roll_axis : str
        Node axis that the bone's Z axis becomes, one of ``AXES``.

    Returns
    -------
    mathutils.Matrix
        4x4 matrix ``K``; a node's axes are ``bone_axes @ K``.

    Raises
    ------
    ValueError
        If an axis name is unknown, or both axes lie on the same line.
    """
    for name in (length_axis, roll_axis):
        if name not in _AXIS_VECTORS:
            raise ValueError(f"Unknown axis '{name}'. Expected one of {AXES}.")
    along = _AXIS_VECTORS[length_axis]
    roll = _AXIS_VECTORS[roll_axis]
    if abs(along.dot(roll)) > 0.5:
        raise ValueError(
            f"Length axis '{length_axis}' and roll axis '{roll_axis}' "
            "must be different lines.")

    # Rotation taking bone coordinates to node coordinates:
    # bone Y -> along, bone Z -> roll, bone X = Y x Z -> along x roll
    bone_to_node = Matrix((along.cross(roll), along, roll)).transposed()
    return bone_to_node.transposed().to_4x4()


def node_matrix(armature_matrix: Matrix, bone_matrix: Matrix,
                axes: Matrix) -> Matrix:
    """
    Compute a node's matrix in FLVER space from a Blender bone.

    Parameters
    ----------
    armature_matrix : mathutils.Matrix
        The armature object's ``matrix_world``.
    bone_matrix : mathutils.Matrix
        The bone's rest matrix in armature space (``Bone.matrix_local``).
    axes : mathutils.Matrix
        Change of axes from :func:`axis_matrix`.

    Returns
    -------
    mathutils.Matrix
        4x4 node matrix in FLVER space.
    """
    blender_world = Y_UP @ armature_matrix @ bone_matrix
    return MIRROR_Z @ blender_world @ MIRROR_Z @ axes


def point_to_flver(world_matrix: Matrix, point: Vector) -> Vector:
    """
    Convert a point from an object's local space to FLVER space.

    Parameters
    ----------
    world_matrix : mathutils.Matrix
        The object's ``matrix_world``.
    point : mathutils.Vector
        Point in the object's local space.

    Returns
    -------
    mathutils.Vector
        The point in FLVER space.
    """
    return MIRROR_Z @ Y_UP @ world_matrix @ point


def local_trs(parent: Optional[Matrix],
              child: Matrix) -> Tuple[Vector, Vector, Vector]:
    """
    Split a node's transform relative to its parent into FLVER fields.

    Parameters
    ----------
    parent : mathutils.Matrix or None
        Parent node matrix in FLVER space, or None for a root node.
    child : mathutils.Matrix
        Node matrix in FLVER space.

    Returns
    -------
    tuple of mathutils.Vector
        ``(translation, rotation, scale)``. Rotation holds Euler radians
        (x, y, z) applied X, then Z, then Y, as FLVER expects.
    """
    local = child if parent is None else parent.inverted() @ child
    translation, rotation, scale = local.decompose()
    euler = rotation.to_matrix().to_euler('XZY')
    return translation, Vector(euler), scale
