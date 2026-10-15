# Compares the exporter's output on a sample .blend with the vanilla node JSON
# saved next to it (same file name, .json), in both modes: From Armature, and
# Merge into Reference JSON with some leaf nodes dropped. Run inside Blender:
#   blender.exe -b sample.blend -P tests/check_samples.py

import json
import math
import os
import sys
import tempfile
from typing import Dict, List, Optional

import bpy
from mathutils import Matrix, Quaternion

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from src.core import vanilla_axes, writer  # noqa: E402
from src.core.transforms import world_matrices  # noqa: E402
from src.operators import find_armature  # noqa: E402

TOLERANCE = 1e-4
CORE_BONES = ('L_Clavicle', 'R_Clavicle', 'L_UpperArm', 'R_UpperArm',
              'L_Forearm', 'R_Forearm', 'L_Thigh', 'R_Thigh', 'Neck',
              'L_Finger1', 'R_Finger1')


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


MERGE_DROPPED = 20


def merge_check(armature_obj: bpy.types.Object, vanilla: List[dict], name: str) -> List[str]:
    """
    Drop leaf nodes from the vanilla list, merge the armature back in, and compare.

    The last ``MERGE_DROPPED`` leaf nodes whose bone and parent bone exist in
    Blender are removed. After the merge, every kept node must have the
    vanilla values and parent (by name), and every re-added node must come
    after the last node with Flags 8 or 10, with its joint position and box
    (turned into vanilla axes) within ``TOLERANCE``.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The sample's armature.
    vanilla : list of dict
        The vanilla node list.
    name : str
        Sample name, for the printed report.

    Returns
    -------
    list of str
        Failure messages; empty when the check passes.
    """
    bones = set(armature_obj.data.bones.keys())
    leaves = [n['Name'] for n in vanilla
              if n['FirstChildIndex'] == -1 and n['Name'] in bones and n['ParentIndex'] >= 0
              and vanilla[n['ParentIndex']]['Name'] in bones][-MERGE_DROPPED:]
    dropped = set(leaves)
    partial = [dict(n) for n in vanilla if n['Name'] not in dropped]
    index_of = {n['Name']: i for i, n in enumerate(partial)}
    for n in partial:
        parent = n['ParentIndex']
        n['ParentIndex'] = index_of[vanilla[parent]['Name']] if parent >= 0 else -1

    merged, plan = writer.merge_nodes(armature_obj, partial)
    failures: List[str] = []
    if sorted(plan.added) != sorted(leaves):
        failures.append(f'merge added {sorted(plan.added)[:3]}..., expected the dropped leaves')

    van_by_name = {n['Name']: i for i, n in enumerate(vanilla)}
    out_worlds = world_matrices(merged)
    van_worlds = world_matrices(vanilla)

    def parent_name(nodes, i):
        parent = nodes[i]['ParentIndex']
        return nodes[parent]['Name'] if parent >= 0 else None

    # Kept nodes: same values and parent; indices shift by design
    value_keys = ('Translation', 'Rotation', 'Scale', 'BoundingBoxMin', 'BoundingBoxMax', 'Flags')
    changed = [n['Name'] for i, n in enumerate(merged) if n['Name'] not in dropped and (
        any(n[k] != vanilla[van_by_name[n['Name']]][k] for k in value_keys)
        or parent_name(merged, i) != parent_name(vanilla, van_by_name[n['Name']]))]
    if changed:
        failures.append(f'{len(changed)} kept nodes changed, e.g. {changed[:3]}')

    position_error = 0.0
    box_error = 0.0
    for i, n in enumerate(merged):
        if n['Name'] not in dropped:
            continue
        j = van_by_name[n['Name']]
        if i < plan.insertion:
            failures.append(f"re-added '{n['Name']}' is before the insertion point")
        if parent_name(merged, i) != parent_name(vanilla, j):
            failures.append(f"re-added '{n['Name']}' has another parent")
        position_error = max(position_error,
                             (out_worlds[i].translation - van_worlds[j].translation).length)
        ob = box(n)
        if any(ob[0] + ob[1]):
            turned = turn_box(ob, out_worlds[i], van_worlds[j])
            if turned is None:
                failures.append(f"re-added '{n['Name']}' axes are not a quarter turn apart")
                continue
            box_error = max(box_error, max(abs(x - y) for side in range(2)
                                           for x, y in zip(turned[side], box(vanilla[j])[side])))
    if position_error > TOLERANCE:
        failures.append(f're-added joint positions differ by up to {position_error:.2e}')
    if box_error > TOLERANCE:
        failures.append(f're-added boxes differ by up to {box_error:.2e}')

    print(f'CHECK {name}: merge re-added {len(plan.added)} dropped leaves at {plan.insertion}; '
          f'max position difference {position_error:.2e}, largest box side difference '
          f'{box_error:.2e}; kept nodes changed {len(changed)}')
    return [f'merge: {failure}' for failure in failures]


def vanilla_orientation_check(armature_obj: bpy.types.Object, plain: List[dict],
                              name: str) -> List[str]:
    """
    Check the Vanilla Bone Orientations option against the plain export.

    Parameters
    ----------
    armature_obj : bpy.types.Object
        The sample's armature.
    plain : list of dict
        The export with the option off.
    name : str
        Sample name for the report.

    Returns
    -------
    list of str
        Failures: joint positions that moved by more than ``TOLERANCE``, or
        vanilla-named nodes whose orientation is not the table's.
    """
    turned = writer.build_nodes(armature_obj, vanilla_orientations=True)
    plain_worlds = world_matrices(plain)
    turned_worlds = world_matrices(turned)
    moved = max((a.translation - b.translation).length
                for a, b in zip(plain_worlds, turned_worlds))
    named = [i for i, n in enumerate(turned) if n['Name'] in vanilla_axes.ORIENTATIONS]
    angles = [math.degrees(turned_worlds[i].to_quaternion().rotation_difference(
        Quaternion(vanilla_axes.ORIENTATIONS[turned[i]['Name']])).angle) for i in named]
    turn = max((min(a, 360.0 - a) for a in angles), default=0.0)
    print(f'CHECK {name}: vanilla orientations: {len(named)} nodes turned, joint positions moved '
          f'up to {moved:.2e}, largest angle from the table {turn:.2e} degrees')
    failures = []
    if moved > TOLERANCE:
        failures.append(f'vanilla orientations moved joints by up to {moved:.2e}')
    if turn > 1e-3:
        failures.append(f'vanilla orientations off the table by up to {turn:.2e} degrees')
    return failures


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
        # The samples' own nodes are the reference here, so the vanilla
        # orientations are left off; they are checked separately below
        writer.write_nodes(out_path, writer.build_nodes(armature_obj, vanilla_orientations=False))
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
    failures += vanilla_orientation_check(armature_obj, output, name)
    failures += merge_check(armature_obj, vanilla, name)
    for failure in failures:
        print(f'CHECK {name}: FAIL {failure}')
    print(f'CHECK {name}: {"PASS" if not failures else "FAIL"}')
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
