# Rewrites a FLVER's SkeletonSet so that it mirrors the node list.
#
# FLVER_Editor's "Load JSON" replaces the node list but writes the SkeletonSet
# back unchanged, so it keeps describing the old node order. This tool writes a
# copy of the FLVER whose SkeletonSet entries mirror the nodes again.
#
# Usage: python tools/fix_skeleton_set.py <input.flver> [<output.flver>]
#
# Layout follows SoulsFormatsNEXT (FLVER2/FLVER2.cs, Node.cs, FLVER2/SkeletonSet.cs).

import os
import struct
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence

MIN_VERSION = 0x2001A
HEADER_SIZE = 128
DUMMY_SIZE = 64
MATERIAL_SIZE = 32
NODE_SIZE = 128
MESH_SIZE = 48
FACE_SET_SIZE = 32
VERTEX_BUFFER_SIZE = 32
BUFFER_LAYOUT_SIZE = 16
TEXTURE_SIZE = 32
SKELETON_HEADER_SIZE = 32
SKELETON_ENTRY_SIZE = 16


class FlverError(ValueError):
    """A FLVER the tool cannot read or will not change."""


class Layout(NamedTuple):
    """Where the node list and the SkeletonSet sit in a FLVER file."""
    node_count: int
    node_offset: int
    skeleton_offset: int
    base_count: int
    base_offset: int
    all_count: int
    all_offset: int


class NodeLinks(NamedTuple):
    """Hierarchy links of one node, as stored in the node list."""
    parent: int
    first_child: int
    next_sibling: int
    previous_sibling: int


def read_layout(data: bytes) -> Layout:
    """
    Locate the node list and the SkeletonSet in a FLVER file.

    Parameters
    ----------
    data : bytes
        The whole FLVER file.

    Returns
    -------
    Layout
        Node count and offset, SkeletonSet offset, and the count and offset
        of both SkeletonSet halves (base and all).

    Raises
    ------
    FlverError
        If the file is not a little-endian FLVER of version 0x2001A or later,
        or the SkeletonSet does not fit the file.
    """
    if len(data) < HEADER_SIZE or data[:6] != b'FLVER\x00':
        raise FlverError("Not a FLVER file.")
    if data[6:8] != b'L\x00':
        raise FlverError("Big-endian FLVER files are not supported.")
    version, = struct.unpack_from('<i', data, 8)
    if version < MIN_VERSION:
        raise FlverError(f"FLVER version {version:#x} has no SkeletonSet "
                         f"(it starts at {MIN_VERSION:#x}).")
    dummies, materials, nodes, meshes, vertex_buffers = struct.unpack_from('<5i', data, 20)
    face_sets, buffer_layouts, textures = struct.unpack_from('<3i', data, 80)
    counts = (dummies, materials, nodes, meshes, vertex_buffers, face_sets,
              buffer_layouts, textures)
    if any(count < 0 for count in counts):
        raise FlverError("FLVER header holds a negative count.")

    node_offset = HEADER_SIZE + dummies * DUMMY_SIZE + materials * MATERIAL_SIZE
    skeleton_offset = (node_offset + nodes * NODE_SIZE + meshes * MESH_SIZE
                       + face_sets * FACE_SET_SIZE
                       + vertex_buffers * VERTEX_BUFFER_SIZE
                       + buffer_layouts * BUFFER_LAYOUT_SIZE
                       + textures * TEXTURE_SIZE)
    if skeleton_offset + SKELETON_HEADER_SIZE > len(data):
        raise FlverError("SkeletonSet header lies past the end of the file.")
    base_count, all_count, base_offset, all_offset = struct.unpack_from(
        '<hhII', data, skeleton_offset)
    if data[skeleton_offset + 12:skeleton_offset + SKELETON_HEADER_SIZE] != bytes(20):
        raise FlverError("SkeletonSet header padding is not zero; layout not recognised.")
    for count, offset in ((base_count, base_offset), (all_count, all_offset)):
        if count < 0 or offset + count * SKELETON_ENTRY_SIZE > len(data):
            raise FlverError("SkeletonSet entries lie past the end of the file.")
    return Layout(nodes, node_offset, skeleton_offset, base_count, base_offset,
                  all_count, all_offset)


def read_nodes(data: bytes, layout: Layout) -> List[NodeLinks]:
    """
    Read the hierarchy links of every node.

    Parameters
    ----------
    data : bytes
        The whole FLVER file.
    layout : Layout
        Result of :func:`read_layout`.

    Returns
    -------
    list of NodeLinks
        One entry per node, in file order.
    """
    nodes = []
    for index in range(layout.node_count):
        at = layout.node_offset + index * NODE_SIZE
        parent, first_child = struct.unpack_from('<hh', data, at + 28)
        next_sibling, previous_sibling = struct.unpack_from('<hh', data, at + 44)
        nodes.append(NodeLinks(parent, first_child, next_sibling, previous_sibling))
    return nodes


def check_node_links(nodes: Sequence[NodeLinks]) -> List[str]:
    """
    List inconsistencies in the node hierarchy links.

    The expected links follow SoulsFormats' convention, the same one
    ``src/core/hierarchy.py`` writes: children of one parent, and root nodes,
    are siblings in file order.

    Parameters
    ----------
    nodes : sequence of NodeLinks
        Links from :func:`read_nodes`.

    Returns
    -------
    list of str
        One message per inconsistent node; empty when the links agree.
    """
    count = len(nodes)
    problems = []
    children: Dict[int, List[int]] = {}
    for index, node in enumerate(nodes):
        if not -1 <= node.parent < count:
            problems.append(f"node {index}: parent {node.parent} is out of range")
            continue
        children.setdefault(node.parent, []).append(index)
    if problems:
        return problems
    for index, node in enumerate(nodes):
        siblings = children[node.parent]
        position = siblings.index(index)
        kids = children.get(index, [])
        expected = NodeLinks(
            node.parent,
            kids[0] if kids else -1,
            siblings[position + 1] if position + 1 < len(siblings) else -1,
            siblings[position - 1] if position > 0 else -1,
        )
        if node != expected:
            problems.append(f"node {index}: links {tuple(node)} should be {tuple(expected)}")
    return problems


def _entry(nodes: Sequence[NodeLinks], index: int) -> bytes:
    """Pack the SkeletonSet entry that mirrors node ``index``."""
    node = nodes[index]
    return struct.pack('<hhhhii', node.parent, node.first_child,
                       node.next_sibling, node.previous_sibling, index, 0)


def mirrored_entries(data: bytes, layout: Layout, nodes: Sequence[NodeLinks]) -> Dict[str, int]:
    """
    Count the SkeletonSet entries that already mirror their node.

    Parameters
    ----------
    data : bytes
        The whole FLVER file.
    layout : Layout
        Result of :func:`read_layout`.
    nodes : sequence of NodeLinks
        Links from :func:`read_nodes`.

    Returns
    -------
    dict of str to int
        Matching entries in the ``base`` and ``all`` halves.
    """
    result = {}
    for half, count, offset in (('base', layout.base_count, layout.base_offset),
                                ('all', layout.all_count, layout.all_offset)):
        result[half] = sum(
            1 for i in range(min(count, len(nodes)))
            if data[offset + i * SKELETON_ENTRY_SIZE:offset + (i + 1) * SKELETON_ENTRY_SIZE]
            == _entry(nodes, i))
    return result


def rebuild_skeleton_set(data: bytes, layout: Layout, nodes: Sequence[NodeLinks]) -> bytes:
    """
    Rewrite both SkeletonSet halves so each entry mirrors its node.

    Entry k becomes (parent, first child, next sibling, previous sibling,
    NodeIndex k, 0) of node k. A half holding more entries than there are
    nodes is shrunk in place: both counts become the node count and the
    entries no longer used are zeroed. Readers take exactly ``count``
    entries from each stored offset (SoulsFormats ``SkeletonSet.cs``), so
    nothing else in the file moves or changes.

    Parameters
    ----------
    data : bytes
        The whole FLVER file.
    layout : Layout
        Result of :func:`read_layout`.
    nodes : sequence of NodeLinks
        Links from :func:`read_nodes`; must pass :func:`check_node_links`.

    Returns
    -------
    bytes
        The rewritten file.

    Raises
    ------
    FlverError
        If either half holds fewer entries than there are nodes (growing
        would move later sections of the file), or the node links are
        inconsistent.
    """
    count = len(nodes)
    if layout.base_count < count or layout.all_count < count:
        raise FlverError(
            f"SkeletonSet holds {layout.base_count} base and {layout.all_count} "
            f"entries for {count} nodes; growing it is not supported.")
    problems = check_node_links(nodes)
    if problems:
        raise FlverError("Node links are inconsistent: " + "; ".join(problems[:5]))
    out = bytearray(data)
    struct.pack_into('<hh', out, layout.skeleton_offset, count, count)
    for offset, stored in ((layout.base_offset, layout.base_count),
                           (layout.all_offset, layout.all_count)):
        for index in range(count):
            at = offset + index * SKELETON_ENTRY_SIZE
            out[at:at + SKELETON_ENTRY_SIZE] = _entry(nodes, index)
        start = offset + count * SKELETON_ENTRY_SIZE
        end = offset + stored * SKELETON_ENTRY_SIZE
        out[start:end] = bytes(end - start)
    return bytes(out)


def default_output(path: str) -> str:
    """
    Name the fixed copy next to the input: ``<name>.skelfix.flver``.

    Parameters
    ----------
    path : str
        Input FLVER path.

    Returns
    -------
    str
        Output path.
    """
    stem, extension = os.path.splitext(path)
    return f"{stem}.skelfix{extension or '.flver'}"


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the tool from the command line.

    Parameters
    ----------
    argv : sequence of str, optional
        ``[input]`` or ``[input, output]``; defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        0 on success, 1 on any error.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) not in (1, 2):
        print("Usage: python tools/fix_skeleton_set.py <input.flver> [<output.flver>]")
        return 1
    source = args[0]
    target = args[1] if len(args) == 2 else default_output(source)
    if os.path.abspath(source) == os.path.abspath(target):
        print("The output must be a different file; the input is never overwritten.")
        return 1
    if os.path.exists(target):
        print(f"Output already exists, not replacing it: {target}")
        return 1
    try:
        with open(source, 'rb') as handle:
            data = handle.read()
        layout = read_layout(data)
        nodes = read_nodes(data, layout)
        before = mirrored_entries(data, layout, nodes)
        fixed = rebuild_skeleton_set(data, layout, nodes)
        check = read_layout(fixed)
        after = mirrored_entries(fixed, check, read_nodes(fixed, check))
    except FlverError as error:
        print(f"Not changed: {error}")
        return 1
    except OSError as error:
        print(f"Could not read {source}: {error}")
        return 1
    if (after != {'base': len(nodes), 'all': len(nodes)}
            or (check.base_count, check.all_count) != (len(nodes), len(nodes))):
        print(f"Internal check failed after rewriting: {after}")
        return 1
    with open(target, 'xb') as handle:
        handle.write(fixed)
    for half, stored in (('base', layout.base_count), ('all', layout.all_count)):
        dropped = stored - len(nodes)
        extra = f", {dropped} unused entries dropped" if dropped else ""
        print(f"{half}: {len(nodes) - before[half]} of {len(nodes)} entries rewritten{extra}")
    print(f"Every SkeletonSet entry now mirrors its node. Written: {target}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
