# Plan a merge of armature bones into a reference node list; plain Python

from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple, Union

from . import messages
from .hierarchy import link_indices
from .messages import ExportError

# Fields every FLVER node in a reference JSON must have
NODE_FIELDS = ('Name', 'ParentIndex', 'FirstChildIndex', 'NextSiblingIndex',
               'PreviousSiblingIndex', 'Translation', 'Rotation', 'Scale',
               'BoundingBoxMin', 'BoundingBoxMax', 'Flags')

# Added bones go after the last reference node with one of these Flags
BONE_FLAGS = (8, 10)

KEEP_INPUT = 'KEEP_INPUT'
BLENDER_KEEP_PLACEMENT = 'BLENDER_KEEP_PLACEMENT'
BLENDER_AS_IS = 'BLENDER_AS_IS'
REPARENT_CHOICES = (KEEP_INPUT, BLENDER_KEEP_PLACEMENT, BLENDER_AS_IS)

# Where an output node comes from: ('input', index in the reference list) or
# ('added', bone name)
Source = Tuple[str, Union[int, str]]


class MergePlan(NamedTuple):
    """
    The node order and parents of a merged node list, before any values.

    Attributes
    ----------
    sources : list of tuple
        Per output node, ``('input', input_index)`` or ``('added', name)``.
    names : list of str
        Per output node, its name.
    parents : list of int
        Per output node, its parent's output index, or -1.
    links : list of dict
        Per output node, ``FirstChildIndex``, ``NextSiblingIndex`` and
        ``PreviousSiblingIndex``.
    recompute : list of int
        Output indices of reference nodes whose values must be recomputed so
        that they keep their placement under a new parent.
    insertion : int
        Output index of the first added node.
    added : list of str
        Names of the added bones, in output order.
    input_only : list of str
        Names of reference nodes that have no bone in the armature.
    reparented : list of str
        Names of reference nodes whose armature parent differs from the reference.
    """
    sources: List[Source]
    names: List[str]
    parents: List[int]
    links: List[Dict[str, int]]
    recompute: List[int]
    insertion: int
    added: List[str]
    input_only: List[str]
    reparented: List[str]


def validate_input(nodes) -> None:
    """
    Check that a parsed JSON value is a usable FLVER node list.

    Parameters
    ----------
    nodes : object
        The value parsed from the reference JSON.

    Raises
    ------
    messages.ExportError
        A ``ValueError``. If it is not a list of node objects with all FLVER fields, a unique
        string ``Name`` each, and parent indices that point at another node.
    """
    if not isinstance(nodes, list):
        raise ExportError(messages.NOT_A_LIST)
    seen = set()
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ExportError(messages.NOT_AN_OBJECT, index=index)
        missing = [field for field in NODE_FIELDS if field not in node]
        if missing:
            raise ExportError(messages.MISSING_FIELDS, index=index, fields=', '.join(missing))
        name = node['Name']
        if not isinstance(name, str) or not name:
            raise ExportError(messages.NO_NAME, index=index)
        if name in seen:
            raise ExportError(messages.DUPLICATE_NAME, name=name)
        seen.add(name)
        parent = node['ParentIndex']
        if not isinstance(parent, int) or not -1 <= parent < len(nodes) or parent == index:
            raise ExportError(messages.BAD_PARENT_INDEX, name=name, parent=parent)


def plan_merge(input_nodes: List[dict],
               bones: Sequence[Tuple[str, Optional[str]]],
               reparent: str = KEEP_INPUT) -> MergePlan:
    """
    Decide the order and parents of the merged node list.

    Reference nodes keep their order. Bones that the reference lacks are
    inserted as one block after the last reference node with Flags 8 or 10 (at 0 if there is
    none), in the order given.

    Parameters
    ----------
    input_nodes : list of dict
        The reference node list; checked with :func:`validate_input`.
    bones : sequence of tuple
        ``(name, parent_name)`` per armature bone, parents first;
        ``parent_name`` is None for a root bone.
    reparent : str
        One of ``REPARENT_CHOICES``: what to do with a reference node whose
        armature parent differs from its reference parent.

    Returns
    -------
    MergePlan
        Order, parents, links and the lists for the report.

    Raises
    ------
    messages.ExportError
        A ``ValueError``. If the reference is invalid, ``reparent`` is unknown, or a node would
        come before its parent.
    """
    validate_input(input_nodes)
    if reparent not in REPARENT_CHOICES:
        raise ExportError(messages.UNKNOWN_REPARENT, choice=reparent,
                          choices=str(REPARENT_CHOICES))

    input_names = [node['Name'] for node in input_nodes]
    input_set = set(input_names)
    bone_parent = dict(bones)
    added = [name for name, _ in bones if name not in input_set]

    insertion = 0
    for index, node in enumerate(input_nodes):
        if node['Flags'] in BONE_FLAGS:
            insertion = index + 1

    sources: List[Source] = (
        [('input', i) for i in range(insertion)]
        + [('added', name) for name in added]
        + [('input', i) for i in range(insertion, len(input_nodes))])
    names = [input_names[ref] if kind == 'input' else ref for kind, ref in sources]
    index_of = {name: i for i, name in enumerate(names)}

    parents: List[int] = []
    recompute: List[int] = []
    input_only: List[str] = []
    reparented: List[str] = []
    for out_index, (kind, ref) in enumerate(sources):
        name = names[out_index]
        if kind == 'added':
            parent_name = bone_parent[name]
        else:
            input_parent = input_nodes[ref]['ParentIndex']
            parent_name = input_names[input_parent] if input_parent >= 0 else None
            if name not in bone_parent:
                input_only.append(name)
            elif bone_parent[name] != parent_name:
                reparented.append(name)
                if reparent != KEEP_INPUT:
                    parent_name = bone_parent[name]
                if reparent == BLENDER_KEEP_PLACEMENT:
                    recompute.append(out_index)
        parents.append(index_of[parent_name] if parent_name is not None else -1)

    for out_index, parent in enumerate(parents):
        if parent > out_index:
            raise ExportError(messages.PARENT_AFTER_CHILD, name=names[out_index],
                              parent=names[parent])

    return MergePlan(sources=sources, names=names, parents=parents,
                     links=link_indices(parents), recompute=recompute,
                     insertion=insertion, added=added, input_only=input_only,
                     reparented=reparented)
