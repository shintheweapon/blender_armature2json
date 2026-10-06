# Compares the exporter's output on a sample .blend with the vanilla node JSON
# saved next to it (same file name, .json). Run inside Blender:
#   blender.exe -b sample.blend -P tests/check_samples.py

import json
import math
import os
import sys
import tempfile
from typing import Dict, List, Optional

import bpy
from mathutils import Euler, Matrix, Vector

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from src.core import writer  # noqa: E402
from src.operators import find_armature  # noqa: E402

TOLERANCE = 1e-4
CORE_BONES = ('L_Clavicle', 'R_Clavicle', 'L_UpperArm', 'R_UpperArm',
              'L_Forearm', 'R_Forearm', 'L_Thigh', 'R_Thigh', 'Neck',
              'L_Finger1', 'R_Finger1')


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
        t, r, s = (node[key] for key in ('Translation', 'Rotation', 'Scale'))
        local = Matrix.LocRotScale(Vector((t['X'], t['Y'], t['Z'])),
                                   Euler((r['X'], r['Y'], r['Z']), 'XZY'),
                                   Vector((s['X'], s['Y'], s['Z'])))
        parent = node['ParentIndex']
        worlds.append(worlds[parent] @ local if parent >= 0 else local)
    return worlds


def box(node: dict) -> List[List[float]]:
    """Return a node's box as ``[[min x, y, z], [max x, y, z]]``."""
    return [[node[key][axis] for axis in 'XYZ']
            for key in ('BoundingBoxMin', 'BoundingBoxMax')]


def turn_box(out_box: List[List[float]], out_world: Matrix,
             van_world: Matrix) -> Optional[List[List[float]]]:
    """
    Express an output box in the vanilla node's axes.

    Parameters
    ----------
    out_box : list of list of float
        ``[[min x, y, z], [max x, y, z]]`` in the output node's axes.
    out_world : mathutils.Matrix
        Output node matrix in FLVER space.
    van_world : mathutils.Matrix
        Vanilla node matrix in FLVER space.

    Returns
    -------
    list of list of float or None
        The box in vanilla axes, or None when the two sets of axes are not
        a whole number of quarter turns apart.
    """
    a = out_world.to_3x3().normalized()
    b = van_world.to_3x3().normalized()
    turn = b.transposed() @ a  # vanilla coordinates of the output axes
    low, high = [0.0] * 3, [0.0] * 3
    for row in range(3):
        col = max(range(3), key=lambda c: abs(turn[row][c]))
        if abs(abs(turn[row][col]) - 1.0) > 1e-3:
            return None
        if turn[row][col] > 0:
            low[row], high[row] = out_box[0][col], out_box[1][col]
        else:
            low[row], high[row] = -out_box[1][col], -out_box[0][col]
    return [low, high]


def main() -> int:
    """
    Run the comparison and print a report.

    Returns
    -------
    int
        0 when every hard check passes, otherwise 1.
    """
    blend_path = bpy.data.filepath
    json_path = os.path.splitext(blend_path)[0] + '.json'
    with open(json_path, encoding='utf-8') as handle:
        vanilla = json.load(handle)

    armature_obj = find_armature(bpy.context)
    with tempfile.TemporaryDirectory() as folder:
        out_path = os.path.join(folder, 'out.json')
        writer.write_nodes(out_path, writer.build_nodes(armature_obj))
        with open(out_path, encoding='utf-8') as handle:
            output = json.load(handle)

    failures: List[str] = []
    name = os.path.basename(blend_path)

    out_by_name: Dict[str, int] = {n['Name']: i for i, n in enumerate(output)}
    van_by_name: Dict[str, int] = {n['Name']: i for i, n in enumerate(vanilla)}
    if set(out_by_name) != set(van_by_name):
        failures.append('node names differ')

    def parent_name(nodes, i):
        parent = nodes[i]['ParentIndex']
        return nodes[parent]['Name'] if parent >= 0 else None

    wrong_parents = [n for n, i in out_by_name.items() if n in van_by_name
                     and parent_name(output, i) != parent_name(vanilla, van_by_name[n])]
    if wrong_parents:
        failures.append(f'{len(wrong_parents)} parents differ, e.g. {wrong_parents[:3]}')

    out_worlds = world_matrices(output)
    van_worlds = world_matrices(vanilla)
    position_error = max((out_worlds[i].translation - van_worlds[van_by_name[n]].translation).length
                         for n, i in out_by_name.items() if n in van_by_name)
    if position_error > TOLERANCE:
        failures.append(f'joint positions differ by up to {position_error:.2e}')

    same_axes = set()
    for n, i in out_by_name.items():
        if n not in van_by_name:
            continue
        a = out_worlds[i].to_3x3().normalized()
        b = van_worlds[van_by_name[n]].to_3x3().normalized()
        if max(math.degrees(a.col[k].angle(b.col[k], 0.0)) for k in range(3)) < 0.1:
            same_axes.add(n)
    core = [n for n in CORE_BONES if n in out_by_name]
    core_matching = [n for n in core if n in same_axes]
    core_differing = [n for n in core if n not in same_axes]

    # Boxes: output and vanilla node axes differ by quarter or half turns
    # (Blender keeps no vanilla axes), so each output box is turned into the
    # vanilla node's axes before its sides are compared.
    box_errors = []
    zero_in_output = 0
    boxes_compared = 0
    largest_box_error = 0.0
    for n, i in out_by_name.items():
        if n not in van_by_name:
            continue
        j = van_by_name[n]
        ob, vb = box(output[i]), box(vanilla[j])
        if not any(ob[0] + ob[1]):
            zero_in_output += 1
            continue
        turned = turn_box(ob, out_worlds[i], van_worlds[j])
        if turned is None:
            box_errors.append((n, 'axes are not a quarter turn apart'))
            continue
        error = max(abs(x - y) for side in range(2) for x, y in zip(turned[side], vb[side]))
        boxes_compared += 1
        largest_box_error = max(largest_box_error, error)
        if error > TOLERANCE:
            box_errors.append((n, error))
    if box_errors:
        failures.append(f'{len(box_errors)} boxes differ, e.g. {box_errors[:3]}')

    print(f'CHECK {name}: {len(output)} nodes exported, {len(vanilla)} in vanilla JSON')
    print(f'CHECK {name}: max joint position difference {position_error:.2e}')
    print(f'CHECK {name}: nodes with vanilla axes {len(same_axes)}; core bones matching '
          f'{len(core_matching)}/{len(core)}, differing {core_differing}')
    print(f'CHECK {name}: boxes compared {boxes_compared}, largest side difference '
          f'{largest_box_error:.2e}; nodes without weighted vertices (zero box) {zero_in_output}')
    for failure in failures:
        print(f'CHECK {name}: FAIL {failure}')
    print(f'CHECK {name}: {"PASS" if not failures else "FAIL"}')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
