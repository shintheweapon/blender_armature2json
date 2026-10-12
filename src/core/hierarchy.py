# Node order and hierarchy links

from typing import TYPE_CHECKING, Dict, List

from . import messages
from .messages import ExportError

if TYPE_CHECKING:
    # Only for type hints, so link_indices imports without Blender
    import bpy


def depth_first_bones(armature: 'bpy.types.Armature') -> List['bpy.types.Bone']:
    """
    List an armature's bones depth first, following Blender's child order.

    Every parent comes before its children, and the children of one parent
    keep the order Blender stores them in.

    Parameters
    ----------
    armature : bpy.types.Armature
        Armature data whose bones are listed.

    Returns
    -------
    list of bpy.types.Bone
        All bones of the armature.
    """
    ordered: List['bpy.types.Bone'] = []
    stack = [b for b in armature.bones if b.parent is None][::-1]
    while stack:
        bone = stack.pop()
        ordered.append(bone)
        stack.extend(reversed(bone.children))
    return ordered


def link_indices(parent_indices: List[int]) -> List[Dict[str, int]]:
    """
    Compute FLVER child and sibling links from parent indices.

    Siblings are ordered by their position in the list. Root nodes (parent
    index -1) are siblings of each other, as in vanilla node lists.

    Parameters
    ----------
    parent_indices : list of int
        Parent index of each node, or -1 for a root node.

    Returns
    -------
    list of dict
        Per node, the keys ``FirstChildIndex``, ``NextSiblingIndex`` and
        ``PreviousSiblingIndex``, each -1 when absent.

    Raises
    ------
    ValueError
        If a parent index does not point at an earlier node.
    """
    children: Dict[int, List[int]] = {}
    for index, parent in enumerate(parent_indices):
        if not -1 <= parent < index:
            raise ExportError(messages.PARENTS_FIRST, index=index, parent=parent)
        children.setdefault(parent, []).append(index)

    links = [{'FirstChildIndex': -1, 'NextSiblingIndex': -1,
              'PreviousSiblingIndex': -1} for _ in parent_indices]
    for parent, kids in children.items():
        if parent >= 0:
            links[parent]['FirstChildIndex'] = kids[0]
        for previous, current in zip(kids, kids[1:]):
            links[previous]['NextSiblingIndex'] = current
            links[current]['PreviousSiblingIndex'] = previous
    return links
