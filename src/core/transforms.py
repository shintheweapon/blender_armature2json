# Transforms between Blender armature space and FLVER node space

import math
from typing import List, Optional, Sequence, Tuple

from mathutils import Euler, Matrix, Vector

from . import messages
from .messages import ExportError

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
            raise ExportError(messages.UNKNOWN_AXIS, name=name, axes=str(AXES))
    along = _AXIS_VECTORS[length_axis]
    roll = _AXIS_VECTORS[roll_axis]
    if abs(along.dot(roll)) > 0.5:
        raise ExportError(messages.SAME_LINE_AXES, length=length_axis, roll=roll_axis)

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
    return translation, matrix_to_euler_xzy(rotation.to_matrix()), scale


def node_local_matrix(node: dict) -> Matrix:
    """
    Build a node's matrix relative to its parent from its stored fields.

    Parameters
    ----------
    node : dict
        FLVER node with ``Translation``, ``Rotation`` (Euler radians, applied
        X, then Z, then Y) and ``Scale``.

    Returns
    -------
    mathutils.Matrix
        4x4 local matrix.
    """
    t, r, s = (node[key] for key in ('Translation', 'Rotation', 'Scale'))
    return Matrix.LocRotScale(Vector((t['X'], t['Y'], t['Z'])),
                              Euler((r['X'], r['Y'], r['Z']), 'XZY'),
                              Vector((s['X'], s['Y'], s['Z'])))


def world_matrices(nodes: List[dict]) -> List[Matrix]:
    """
    Rebuild each node's FLVER-space matrix from its local fields.

    Parameters
    ----------
    nodes : list of dict
        Node list with parents before children.

    Returns
    -------
    list of mathutils.Matrix
        World matrix per node.
    """
    worlds: List[Matrix] = []
    for node in nodes:
        local = node_local_matrix(node)
        parent = node['ParentIndex']
        worlds.append(worlds[parent] @ local if parent >= 0 else local)
    return worlds


Rows = List[List[float]]


def _rows(matrix: Matrix) -> Rows:
    """Copy a 3x3 mathutils matrix into double precision rows."""
    return [[float(matrix[r][c]) for c in range(3)] for r in range(3)]


def _multiply(a: Rows, b: Rows) -> Rows:
    """Multiply two 3x3 matrices given as rows."""
    return [[sum(a[r][k] * b[k][c] for k in range(3)) for c in range(3)]
            for r in range(3)]


def _transpose(a: Rows) -> Rows:
    """Transpose a 3x3 matrix given as rows."""
    return [[a[c][r] for c in range(3)] for r in range(3)]


def _rotation(axis: str, angle: float) -> Rows:
    """Rotation about one axis by ``angle`` radians, as rows."""
    c, s = math.cos(angle), math.sin(angle)
    if axis == 'X':
        return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    if axis == 'Y':
        return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def euler_xzy_to_rows(angles: Sequence[float]) -> Rows:
    """
    Build the rotation for FLVER Euler angles in double precision.

    Parameters
    ----------
    angles : sequence of float
        Radians (x, y, z), applied X, then Z, then Y.

    Returns
    -------
    list of list of float
        3x3 rotation ``Ry @ Rz @ Rx`` as rows.
    """
    x, y, z = angles
    return _multiply(_rotation('Y', y),
                     _multiply(_rotation('Z', z), _rotation('X', x)))


def matrix_to_euler_xzy(rotation: Matrix) -> Vector:
    """
    Split a rotation into FLVER Euler angles, in double precision.

    Z comes from ``atan2`` rather than ``asin`` so it stays accurate close
    to +-90 degrees, Y follows, and X is read from what remains once Y and Z
    are removed. Rebuilding the rotation from the result reproduces the
    input to within rounding, including at gimbal lock.

    Parameters
    ----------
    rotation : mathutils.Matrix
        3x3 rotation matrix.

    Returns
    -------
    mathutils.Vector
        Radians (x, y, z), applied X, then Z, then Y.
    """
    m = _rows(rotation)
    cos_z = math.hypot(m[0][0], m[2][0])
    z = math.atan2(m[1][0], cos_z)
    y = math.atan2(-m[2][0], m[0][0]) if cos_z > 1e-12 else 0.0
    remaining = _multiply(_transpose(_rotation('Z', z)),
                          _multiply(_transpose(_rotation('Y', y)), m))
    x = math.atan2(remaining[2][1], remaining[1][1])
    return Vector((x, y, z))
