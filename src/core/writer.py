# Build FLVER node dictionaries and write them as JSON

import copy
import json
from typing import Dict, Iterable, List, Tuple

import bpy
from mathutils import Matrix

from . import bounds, files, hierarchy, merge, messages, transforms
from .messages import ExportError

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
                mark_root_as_mesh: bool = False,
                space: str = transforms.DEFAULT_SPACE) -> List[dict]:
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
    space : str
        Coordinate Space, one of ``transforms.SPACES``: how Blender
        coordinates become FLVER coordinates.

    Returns
    -------
    list of dict
        One dictionary per bone, keys in ``FLVER.Node`` field order.

    Raises
    ------
    ValueError
        If the object is not an armature, has no bones, or the axes or the
        space are invalid.
    """
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        raise ExportError(messages.NO_ARMATURE)
    bones = hierarchy.depth_first_bones(armature_obj.data)
    if not bones:
        raise ExportError(messages.NO_BONES, name=armature_obj.name)

    axes = transforms.axis_matrix(length_axis, roll_axis)
    mapping = transforms.space_mapping(space, armature_obj.matrix_world)
    index_of = {bone.name: i for i, bone in enumerate(bones)}
    parents = [index_of[b.parent.name] if b.parent else -1 for b in bones]
    links = hierarchy.link_indices(parents)
    matrices = [transforms.node_matrix(mapping, armature_obj.matrix_world,
                                       bone.matrix_local, axes)
                for bone in bones]
    points = bounds.weighted_points(bounds.skinned_meshes(armature_obj),
                                    index_of.keys(), mapping)

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


def merge_nodes(armature_obj: bpy.types.Object,
                input_nodes: List[dict],
                length_axis: str = transforms.DEFAULT_LENGTH_AXIS,
                roll_axis: str = transforms.DEFAULT_ROLL_AXIS,
                reparent: str = merge.KEEP_INPUT,
                space: str = transforms.DEFAULT_SPACE) -> Tuple[List[dict], merge.MergePlan]:
    """
    Merge an armature's bones into a reference node list.

    Reference nodes are copied unchanged, except their parent and link indices
    and, for ``BLENDER_KEEP_PLACEMENT``, the values of reparented nodes. Bones
    the reference lacks are added with Flags 8 after the last reference node
    with Flags 8 or 10. An added node's values are relative to its parent as
    written in the output, so it lands where the bone is even when that
    parent keeps the reference's axes.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The armature object whose bones are merged.
    input_nodes : list of dict
        The reference node list, for example a vanilla one from FLVER_Editor.
    length_axis : str
        Node axis along each added bone, one of ``transforms.AXES``.
    roll_axis : str
        Node axis that each added bone's Z axis becomes.
    reparent : str
        One of ``merge.REPARENT_CHOICES``.
    space : str
        Coordinate Space for the added bones, one of ``transforms.SPACES``.

    Returns
    -------
    tuple
        ``(nodes, plan)``: the merged node list, and the
        :class:`merge.MergePlan` with the lists for the report.

    Raises
    ------
    ValueError
        If the object is not an armature, has no bones, the reference is invalid,
        the axes or the space are invalid, or a node would come before its
        parent.
    """
    if armature_obj is None or armature_obj.type != 'ARMATURE':
        raise ExportError(messages.NO_ARMATURE)
    bones = hierarchy.depth_first_bones(armature_obj.data)
    if not bones:
        raise ExportError(messages.NO_BONES, name=armature_obj.name)
    plan = merge.plan_merge(
        input_nodes, [(b.name, b.parent.name if b.parent else None) for b in bones],
        reparent)

    axes = transforms.axis_matrix(length_axis, roll_axis)
    mapping = transforms.space_mapping(space, armature_obj.matrix_world)
    bone_by_name = {bone.name: bone for bone in bones}
    points = bounds.weighted_points(bounds.skinned_meshes(armature_obj), plan.added,
                                    mapping)
    input_worlds = transforms.world_matrices(input_nodes)
    recompute = set(plan.recompute)

    worlds = []
    nodes = []
    for i, (kind, ref) in enumerate(plan.sources):
        parent = plan.parents[i]
        parent_world = worlds[parent] if parent >= 0 else None
        if kind == 'added':
            world = transforms.node_matrix(mapping, armature_obj.matrix_world,
                                           bone_by_name[ref].matrix_local, axes)
            translation, rotation, scale = transforms.local_trs(parent_world, world)
            box_min, box_max = bounds.bounding_box(world, points.get(ref, []))
            node = {
                'Name': ref,
                'ParentIndex': parent,
                'FirstChildIndex': -1,
                'NextSiblingIndex': -1,
                'PreviousSiblingIndex': -1,
                'Translation': _xyz(translation),
                'Rotation': _xyz(rotation),
                'Scale': _xyz(scale),
                'BoundingBoxMin': _xyz(box_min),
                'BoundingBoxMax': _xyz(box_max),
                'Flags': FLAG_BONE,
            }
        else:
            node = copy.deepcopy(input_nodes[ref])
            node['ParentIndex'] = parent
            if i in recompute:
                # Same place and axes as in the reference, relative to the new parent
                world = input_worlds[ref]
                translation, rotation, scale = transforms.local_trs(parent_world, world)
                node['Translation'] = _xyz(translation)
                node['Rotation'] = _xyz(rotation)
                node['Scale'] = _xyz(scale)
            else:
                local = transforms.node_local_matrix(node)
                world = parent_world @ local if parent_world is not None else local
        node.update(plan.links[i])
        nodes.append(node)
        worlds.append(world)
    return nodes, plan


def write_nodes(filepath: str, nodes: List[dict]) -> None:
    """
    Write a node list as compact JSON, UTF-8 without BOM, as FLVER_Editor does.

    The file is written through a temporary file in the same folder and
    then moved into place, so a failed export leaves an existing file
    untouched.

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
    files.write_text_atomic(filepath, json.dumps(nodes, separators=(',', ':')))
