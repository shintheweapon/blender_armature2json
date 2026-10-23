# Vanilla orientations on the armature: read a reference node JSON (the
# vanilla character skeleton's) and turn the armature's bones of the same
# names so that the export writes the reference's axes for them

import json
from typing import Dict, List

import bpy
from mathutils import Matrix

from . import messages, transforms
from .messages import ExportError


def load_reference(filepath: str) -> Dict[str, Matrix]:
    """
    Read a node JSON and return each node's rotation in FLVER space.

    Parameters
    ----------
    filepath : str
        Path of a node JSON as FLVER_Editor writes it (a BOM is accepted).

    Returns
    -------
    dict of str to mathutils.Matrix
        Node name to its 3x3 world rotation.

    Raises
    ------
    OSError
        If the file cannot be read.
    json.JSONDecodeError
        If the file is not valid JSON.
    ValueError
        If the file is not a list of nodes.
    """
    with open(filepath, encoding='utf-8-sig') as handle:
        nodes = json.load(handle)
    if not isinstance(nodes, list):
        raise ExportError(messages.NOT_A_LIST)
    worlds = transforms.world_matrices(nodes)
    return {node['Name']: world.to_3x3().normalized() for node, world in zip(nodes, worlds)}


def bone_rotation_for_node(space: transforms.Space, armature_world: Matrix,
                           node_rotation: Matrix, axes: Matrix) -> Matrix:
    """
    Find the bone rotation, in armature space, that exports as a node rotation.

    This is the inverse of the rotation part of :func:`transforms.node_matrix`.

    Parameters
    ----------
    space : transforms.Space
        The Coordinate Space mapping used for the export.
    armature_world : mathutils.Matrix
        The armature object's ``matrix_world``.
    node_rotation : mathutils.Matrix
        3x3 rotation the node should have in FLVER space.
    axes : mathutils.Matrix
        Change of axes from :func:`transforms.axis_matrix`.

    Returns
    -------
    mathutils.Matrix
        3x3 rotation for ``Bone.matrix_local``.
    """
    to_blender = (space.to_flver @ armature_world).to_3x3().inverted()
    return (to_blender @ node_rotation @ axes.to_3x3().inverted()
            @ space.tail.to_3x3().inverted())


def match_orientations(armature_obj: bpy.types.Object, reference: Dict[str, Matrix],
                       space: transforms.Space, axes: Matrix) -> List[str]:
    """
    Turn the armature's bones that are named in ``reference`` to its axes.

    Each matched bone keeps its head and length and gets the rotation that
    exports as the reference node's rotation, with the given space and axes.
    Matched bones and their children are disconnected first, so no child
    moves. Bones of other names are unchanged. X-Axis Mirror is switched off
    while the bones are edited, so no edit is copied onto a bone of the
    other side. The armature's mode, its X-Axis Mirror setting and the
    active object are restored afterwards.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The armature object; it is made active while editing.
    reference : dict of str to mathutils.Matrix
        Node name to 3x3 rotation in FLVER space, as :func:`load_reference`
        returns.
    space : transforms.Space
        The Coordinate Space mapping the export will use.
    axes : mathutils.Matrix
        Change of axes the export will use.

    Returns
    -------
    list of str
        The names of the bones turned, sorted.
    """
    view_layer = bpy.context.view_layer
    previous_active = view_layer.objects.active
    previous_mode = armature_obj.mode
    previous_mirror = armature_obj.data.use_mirror_x
    world = armature_obj.matrix_world.copy()
    view_layer.objects.active = armature_obj
    if previous_mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    try:
        armature_obj.data.use_mirror_x = False
        matched = [b for b in armature_obj.data.edit_bones if b.name in reference]
        for bone in matched:
            bone.use_connect = False
            for child in bone.children:
                child.use_connect = False
        for bone in matched:
            # Setting the matrix keeps the bone's length
            frame = bone_rotation_for_node(space, world, reference[bone.name], axes).to_4x4()
            frame.translation = bone.head.copy()
            bone.matrix = frame
    finally:
        armature_obj.data.use_mirror_x = previous_mirror
        if previous_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=previous_mode)
        view_layer.objects.active = previous_active
    return sorted(b.name for b in armature_obj.data.bones if b.name in reference)
