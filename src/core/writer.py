# Build FLVER node dictionaries and write them as JSON

import json
from typing import Dict, Iterable, List

import bpy

from . import bounds, hierarchy, transforms

FLAG_MESH = 4
FLAG_BONE = 8


def _number(value: float):
    """
    Round a value to single precision and drop the decimals of whole numbers.

    Parameters
    ----------
    value : float
        Value to format.

    Returns
    -------
    int or float
        ``int`` for whole numbers (written as ``1``, as in vanilla files),
        otherwise the value rounded to 9 significant digits.
    """
    rounded = float(f'{value:.9g}')
    return int(rounded) if rounded.is_integer() else rounded


def _xyz(vector: Iterable[float]) -> Dict[str, float]:
    """
    Convert a 3D vector to FLVER's ``{"X", "Y", "Z"}`` form.

    Parameters
    ----------
    vector : iterable of float
        Three components.

    Returns
    -------
    dict
        Keys ``X``, ``Y`` and ``Z``.
    """
    x, y, z = vector
    return {'X': _number(x), 'Y': _number(y), 'Z': _number(z)}


def build_nodes(armature_obj: bpy.types.Object,
                length_axis: str = transforms.DEFAULT_LENGTH_AXIS,
                roll_axis: str = transforms.DEFAULT_ROLL_AXIS,
                mark_root_as_mesh: bool = True) -> List[dict]:
    """
    Build the FLVER node list for an armature.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The armature object to export.
    length_axis : str
        Node axis along each bone, one of ``transforms.AXES``.
    roll_axis : str
        Node axis that each bone's Z axis becomes, one of ``transforms.AXES``.
    mark_root_as_mesh : bool
        Write node 0 with Flags 12 (Mesh and Bone) instead of 8 (Bone).

    Returns
    -------
    list of dict
        One dictionary per bone, keys in ``FLVER.Node`` field order.

    Raises
    ------
    ValueError
        If the object is not an armature, has no bones, or the axes are
        invalid.
    """
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        raise ValueError("Select an armature object to export.")
    bones = hierarchy.depth_first_bones(armature_obj.data)
    if not bones:
        raise ValueError(f"Armature '{armature_obj.name}' has no bones.")

    axes = transforms.axis_matrix(length_axis, roll_axis)
    index_of = {bone.name: i for i, bone in enumerate(bones)}
    parents = [index_of[b.parent.name] if b.parent else -1 for b in bones]
    links = hierarchy.link_indices(parents)
    matrices = [transforms.node_matrix(armature_obj.matrix_world,
                                       bone.matrix_local, axes)
                for bone in bones]
    points = bounds.weighted_points(bounds.skinned_meshes(armature_obj),
                                    index_of.keys())

    nodes = []
    for i, bone in enumerate(bones):
        parent_matrix = matrices[parents[i]] if parents[i] >= 0 else None
        translation, rotation, scale = transforms.local_trs(parent_matrix,
                                                            matrices[i])
        box_min, box_max = bounds.bounding_box(matrices[i],
                                               points.get(bone.name, []))
        flags = FLAG_BONE
        if i == 0 and mark_root_as_mesh:
            flags |= FLAG_MESH
        nodes.append({
            'Name': bone.name,
            'ParentIndex': parents[i],
            'FirstChildIndex': links[i]['FirstChildIndex'],
            'NextSiblingIndex': links[i]['NextSiblingIndex'],
            'PreviousSiblingIndex': links[i]['PreviousSiblingIndex'],
            'Translation': _xyz(translation),
            'Rotation': _xyz(rotation),
            'Scale': _xyz(scale),
            'BoundingBoxMin': _xyz(box_min),
            'BoundingBoxMax': _xyz(box_max),
            'Flags': flags,
        })
    return nodes


def write_nodes(filepath: str, nodes: List[dict]) -> None:
    """
    Write a node list as compact JSON, UTF-8 without BOM, as FLVER_Editor does.

    Parameters
    ----------
    filepath : str
        Output path.
    nodes : list of dict
        Nodes from :func:`build_nodes`.

    Raises
    ------
    OSError
        If the file cannot be written.
    """
    with open(filepath, 'w', encoding='utf-8', newline='') as handle:
        json.dump(nodes, handle, separators=(',', ':'))
