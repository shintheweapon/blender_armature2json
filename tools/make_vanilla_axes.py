# Builds src/core/vanilla_axes.py: the world orientation of every bone in use in
# vanilla Elden Ring FLVERs, which the exporter's "Vanilla Bone Orientations"
# option gives to bones of the same name.
#
# Usage: python tools/make_vanilla_axes.py <output.py> <input.flver> [<input.flver> ...]
#
# The first input that has a bone wins; later inputs only report how far they
# disagree. Layout follows SoulsFormatsNEXT (FLVER2/FLVER2.cs header, Node.cs).

import datetime
import math
import os
import struct
import sys
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

HEADER_SIZE = 128
DUMMY_SIZE = 64
MATERIAL_SIZE = 32
NODE_SIZE = 128
UNICODE_OFFSET = 73  # FLVER2.cs: Header.Unicode, after the vertex index size byte
FLAG_DISABLED = 1

Rows = List[List[float]]
Quaternion = Tuple[float, float, float, float]


class FlverError(ValueError):
    """A FLVER the tool cannot read."""


class Node(NamedTuple):
    """The fields of one FLVER node that the tool needs."""
    name: str
    parent: int
    rotation: Tuple[float, float, float]
    scale: Tuple[float, float, float]
    flags: int


def _read_name(data: bytes, offset: int, unicode: bool) -> str:
    """
    Read a zero-terminated node name.

    Parameters
    ----------
    data : bytes
        The whole FLVER file.
    offset : int
        Where the name starts.
    unicode : bool
        UTF-16 (little-endian) when True, Shift-JIS otherwise.

    Returns
    -------
    str
        The name.

    Raises
    ------
    FlverError
        If the name runs past the end of the file.
    """
    if unicode:
        end = offset
        while data[end:end + 2] != b'\x00\x00':
            end += 2
            if end >= len(data):
                raise FlverError("A node name runs past the end of the file.")
        return data[offset:end].decode('utf-16-le')
    end = data.find(b'\x00', offset)
    if end < 0:
        raise FlverError("A node name runs past the end of the file.")
    return data[offset:end].decode('shift_jis')


def read_nodes(data: bytes) -> List[Node]:
    """
    Read every node of a FLVER file.

    Parameters
    ----------
    data : bytes
        The whole FLVER file.

    Returns
    -------
    list of Node
        One entry per node, in file order.

    Raises
    ------
    FlverError
        If the file is not a little-endian FLVER or its node list does not fit.
    """
    if len(data) < HEADER_SIZE or data[:6] != b'FLVER\x00':
        raise FlverError("Not a FLVER file.")
    if data[6:8] != b'L\x00':
        raise FlverError("Big-endian FLVER files are not supported.")
    unicode = data[UNICODE_OFFSET] != 0
    dummies, materials, count = struct.unpack_from('<3i', data, 20)
    if min(dummies, materials, count) < 0:
        raise FlverError("FLVER header holds a negative count.")
    start = HEADER_SIZE + dummies * DUMMY_SIZE + materials * MATERIAL_SIZE
    if start + count * NODE_SIZE > len(data):
        raise FlverError("The node list runs past the end of the file.")
    nodes = []
    for index in range(count):
        at = start + index * NODE_SIZE
        name_offset, = struct.unpack_from('<i', data, at + 12)
        rotation = struct.unpack_from('<3f', data, at + 16)
        parent, = struct.unpack_from('<h', data, at + 28)
        scale = struct.unpack_from('<3f', data, at + 32)
        flags, = struct.unpack_from('<i', data, at + 60)
        nodes.append(Node(_read_name(data, name_offset, unicode), parent, rotation,
                          scale, flags))
    return nodes


def _multiply(a: Rows, b: Rows) -> Rows:
    """Multiply two 3x3 matrices given as rows."""
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _rotation(axis: str, angle: float) -> Rows:
    """
    A right-handed rotation about one axis, for column vectors.

    Parameters
    ----------
    axis : str
        'X', 'Y' or 'Z'.
    angle : float
        Angle in radians.

    Returns
    -------
    list of list of float
        The 3x3 matrix as rows.
    """
    c, s = math.cos(angle), math.sin(angle)
    if axis == 'X':
        return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]
    if axis == 'Y':
        return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def local_rotation(angles: Sequence[float]) -> Rows:
    """
    The rotation of SoulsFormats' ``Node.ComputeLocalTransform``.

    Parameters
    ----------
    angles : sequence of float
        The node's Euler angles (x, y, z) in radians.

    Returns
    -------
    list of list of float
        Ry @ Rz @ Rx for column vectors, which is Rx · Rz · Ry in the row-vector
        form SoulsFormats uses.
    """
    x, y, z = angles
    return _multiply(_rotation('Y', y), _multiply(_rotation('Z', z), _rotation('X', x)))


def to_quaternion(m: Rows) -> Quaternion:
    """
    Convert a rotation matrix to a unit quaternion.

    Parameters
    ----------
    m : list of list of float
        3x3 rotation matrix as rows, for column vectors.

    Returns
    -------
    tuple of float
        (w, x, y, z), normalised, with w >= 0.
    """
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = 2.0 * math.sqrt(trace + 1.0)
        q = (0.25 * s, (m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = 2.0 * math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2])
        q = ((m[2][1] - m[1][2]) / s, 0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s)
    elif m[1][1] > m[2][2]:
        s = 2.0 * math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2])
        q = ((m[0][2] - m[2][0]) / s, (m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s)
    else:
        s = 2.0 * math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1])
        q = ((m[1][0] - m[0][1]) / s, (m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s)
    length = math.sqrt(sum(c * c for c in q))
    q = tuple(c / length for c in q)
    return q if q[0] >= 0.0 else tuple(-c for c in q)


def world_orientations(nodes: Sequence[Node]) -> Dict[str, Quaternion]:
    """
    World orientation of every node in use.

    Parameters
    ----------
    nodes : sequence of Node
        A FLVER's nodes in file order.

    Returns
    -------
    dict
        Name to (w, x, y, z), for nodes that are not Disabled (Flags bit 1)
        and have no Disabled ancestor. Scale is left out: it is applied
        before the rotation, so it changes no orientation as long as
        ancestors are uniformly scaled. In the vanilla parts read so far,
        the only bones in use with a scale other than 1 are L_Pectoral and
        R_Pectoral (about 1.0008 and 0.9998 along their own X), and neither
        has children.

    Raises
    ------
    FlverError
        If a parent index is out of range or the hierarchy has a loop.
    """
    worlds: Dict[int, Rows] = {}
    unused = set()

    def world(index: int, seen: Tuple[int, ...] = ()) -> Rows:
        if index in worlds:
            return worlds[index]
        if index in seen:
            raise FlverError("The node hierarchy has a loop.")
        node = nodes[index]
        rotation = local_rotation(node.rotation)
        if node.flags & FLAG_DISABLED:
            unused.add(index)
        if node.parent >= 0:
            if node.parent >= len(nodes):
                raise FlverError(f"Node {index} has parent {node.parent}, past the node list.")
            rotation = _multiply(world(node.parent, seen + (index,)), rotation)
            if node.parent in unused:
                unused.add(index)
        worlds[index] = rotation
        return rotation

    for index in range(len(nodes)):
        world(index)
    return {nodes[i].name: to_quaternion(worlds[i]) for i in range(len(nodes)) if i not in unused}


def angle_between(a: Quaternion, b: Quaternion) -> float:
    """
    Angle of the rotation that turns orientation ``a`` into ``b``.

    Returns
    -------
    float
        Degrees, from 0 to 180.
    """
    dot = min(1.0, abs(sum(x * y for x, y in zip(a, b))))
    return math.degrees(2.0 * math.acos(dot))


def merge_tables(tables: Sequence[Dict[str, Quaternion]]) -> Tuple[Dict[str, Quaternion], Dict[str, float]]:
    """
    Combine per-file tables; the first file that has a name wins.

    Parameters
    ----------
    tables : sequence of dict
        One table per input file, in priority order.

    Returns
    -------
    tuple
        ``(table, disagreement)``: the combined table, and per name the
        largest angle in degrees between the kept orientation and any later
        file's.
    """
    combined: Dict[str, Quaternion] = {}
    disagreement: Dict[str, float] = {}
    for table in tables:
        for name, orientation in table.items():
            if name in combined:
                angle = angle_between(combined[name], orientation)
                disagreement[name] = max(disagreement.get(name, 0.0), angle)
            else:
                combined[name] = orientation
    return combined, disagreement


def _number(value: float) -> str:
    """Write a value with 9 significant digits."""
    return f'{value:.9g}'


def render_module(table: Dict[str, Quaternion], sources: Sequence[str]) -> str:
    """
    Write the table as a Python module.

    Parameters
    ----------
    table : dict
        Name to (w, x, y, z).
    sources : sequence of str
        Input file names, for the header.

    Returns
    -------
    str
        The module text, names sorted.
    """
    lines = [
        "# World orientations of the bones in use in vanilla Elden Ring FLVERs, as unit",
        "# quaternions (w, x, y, z) in FLVER space. Generated by tools/make_vanilla_axes.py",
        f"# on {datetime.date.today().isoformat()} from: {', '.join(sources)}.",
        "# Do not edit by hand; run the tool again instead.",
        "",
        "ORIENTATIONS = {",
    ]
    for name in sorted(table):
        values = ', '.join(_number(c) for c in table[name])
        lines.append(f"    {name!r}: ({values}),")
    lines.append("}")
    return '\n'.join(lines) + '\n'


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the tool from the command line.

    Parameters
    ----------
    argv : sequence of str, optional
        ``[output, input, ...]``; defaults to ``sys.argv[1:]``.

    Returns
    -------
    int
        0 on success, 1 on any error.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("Usage: python tools/make_vanilla_axes.py <output.py> <input.flver> [<input.flver> ...]")
        return 1
    target, sources = args[0], args[1:]
    tables = []
    for source in sources:
        try:
            with open(source, 'rb') as handle:
                tables.append(world_orientations(read_nodes(handle.read())))
        except FlverError as error:
            print(f"Cannot use {source}: {error}")
            return 1
        except OSError as error:
            print(f"Could not read {source}: {error}")
            return 1
    table, disagreement = merge_tables(tables)
    with open(target, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(render_module(table, [os.path.basename(s) for s in sources]))
    print(f"Wrote {len(table)} orientations to {target}")
    for name, angle in sorted(disagreement.items(), key=lambda item: -item[1])[:5]:
        print(f"  largest disagreement: {name} {angle:.3f} degrees")
    return 0


if __name__ == '__main__':
    sys.exit(main())
