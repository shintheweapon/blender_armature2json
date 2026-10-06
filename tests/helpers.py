# Shared helpers that build small Blender scenes for tests

from typing import Dict, Iterable, Optional, Tuple

import bpy

BoneSpec = Tuple[str, Optional[str], Tuple[float, float, float],
                 Tuple[float, float, float], float]


def new_scene() -> None:
    """Empty the current file so each test starts from a clean scene."""
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_armature(bones: Iterable[BoneSpec],
                  name: str = 'Armature') -> bpy.types.Object:
    """
    Create an armature object from bone specifications.

    Parameters
    ----------
    bones : iterable of tuple
        ``(name, parent_name, head, tail, roll)`` per bone, parents first.
    name : str
        Name for the armature object and data.

    Returns
    -------
    bpy.types.Object
        The armature object, linked to the scene and in Object mode.
    """
    data = bpy.data.armatures.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones: Dict[str, bpy.types.EditBone] = {}
    for bone_name, parent_name, head, tail, roll in bones:
        eb = data.edit_bones.new(bone_name)
        eb.head = head
        eb.tail = tail
        eb.roll = roll
        if parent_name is not None:
            eb.parent = edit_bones[parent_name]
        edit_bones[bone_name] = eb
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def make_skinned_box(armature_obj: bpy.types.Object, bone_name: str,
                     size: Tuple[float, float, float],
                     name: str = 'Box') -> bpy.types.Object:
    """
    Create a box mesh from the origin to ``size``, fully weighted to one bone.

    The mesh gets an Armature modifier targeting ``armature_obj`` and one
    vertex group named ``bone_name`` holding all corners at weight 1.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        Armature the box is skinned to.
    bone_name : str
        Bone that receives all the weight.
    size : tuple of float
        Box extent along Blender X, Y and Z.
    name : str
        Name for the mesh object and data.

    Returns
    -------
    bpy.types.Object
        The mesh object, linked to the scene.
    """
    sx, sy, sz = size
    corners = [(x, y, z) for x in (0.0, sx) for y in (0.0, sy) for z in (0.0, sz)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(corners, [], [])
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(corners))), 1.0, 'REPLACE')
    modifier = obj.modifiers.new('Armature', 'ARMATURE')
    modifier.object = armature_obj
    return obj
