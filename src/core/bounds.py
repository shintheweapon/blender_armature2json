# Per-node bounding boxes from weighted mesh vertices

from typing import Dict, Iterable, List, Optional, Tuple

import bpy
from mathutils import Matrix, Vector

from .transforms import point_to_flver

Box = Tuple[Vector, Vector]


def skinned_meshes(armature_obj: bpy.types.Object) -> List[bpy.types.Object]:
    """
    Find the mesh objects deformed by an armature.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The armature object.

    Returns
    -------
    list of bpy.types.Object
        Mesh objects with an Armature modifier that targets ``armature_obj``.
    """
    return [obj for obj in bpy.data.objects
            if obj.type == 'MESH' and any(
                mod.type == 'ARMATURE' and mod.object == armature_obj
                for mod in obj.modifiers)]


def weighted_points(meshes: Iterable[bpy.types.Object],
                    bone_names: Iterable[str]) -> Dict[str, List[Vector]]:
    """
    Collect, per bone, the vertices weighted to it, in FLVER space.

    Vertices are taken in their rest position (the mesh data without
    modifiers), placed by the mesh object's ``matrix_world``.

    Parameters
    ----------
    meshes : iterable of bpy.types.Object
        Mesh objects to read.
    bone_names : iterable of str
        Bones to collect points for; other vertex groups are skipped.

    Returns
    -------
    dict of str to list of mathutils.Vector
        Points per bone name, for bones with at least one vertex of
        weight above zero.
    """
    wanted = set(bone_names)
    points: Dict[str, List[Vector]] = {}
    for obj in meshes:
        group_names = {group.index: group.name for group in obj.vertex_groups}
        matrix = obj.matrix_world
        for vertex in obj.data.vertices:
            position: Optional[Vector] = None
            for element in vertex.groups:
                name = group_names.get(element.group)
                if element.weight <= 0.0 or name not in wanted:
                    continue
                if position is None:
                    position = point_to_flver(matrix, vertex.co)
                points.setdefault(name, []).append(position)
    return points


def bounding_box(node: Matrix, points: List[Vector]) -> Box:
    """
    Compute a node's box around points, in the node's own axes.

    Parameters
    ----------
    node : mathutils.Matrix
        The node's matrix in FLVER space.
    points : list of mathutils.Vector
        Points in FLVER space; an empty list gives a zero box.

    Returns
    -------
    tuple of mathutils.Vector
        ``(minimum, maximum)`` corners.
    """
    if not points:
        return Vector((0.0, 0.0, 0.0)), Vector((0.0, 0.0, 0.0))
    to_node = node.inverted()
    local = [to_node @ p for p in points]
    minimum = Vector([min(p[axis] for p in local) for axis in range(3)])
    maximum = Vector([max(p[axis] for p in local) for axis in range(3)])
    return minimum, maximum
