# Tests for tools/make_vanilla_axes.py and the table it wrote (core.vanilla_axes);
# plain Python, plus one cross-check that needs Blender and the game files

import math
import os
import struct
import sys
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from core import vanilla_axes  # noqa: E402
from tools import make_vanilla_axes as tool  # noqa: E402

HALF = math.pi / 2
ROOT_TO_HALF = math.sqrt(0.5)
# (name, parent, rotation, flags): Root turned 90 degrees about Y; Child a
# further 90 degrees about X; Off is Disabled and hides its child OffChild
NODES = [
    ('Root', -1, (0.0, HALF, 0.0), 8),
    ('Child', 0, (HALF, 0.0, 0.0), 8),
    ('Off', 0, (0.3, 0.0, 0.0), 9),
    ('OffChild', 2, (0.0, 0.0, 0.0), 8),
]
FC_F_0000 = (r"<ELDEN RING>\Game\parts"
             r"\fc_f_0000-partsbnd-dcx\FC_F_0000.flver")
IMPORTER_DIR = r"<blender_flver_importer>"


def build_flver(nodes=NODES, unicode=True):
    """
    Build a minimal FLVER: header, nodes and their names, nothing else.

    Parameters
    ----------
    nodes : list of tuple
        (name, parent, rotation, flags) per node.
    unicode : bool
        Write names as UTF-16 (header Unicode byte set) or Shift-JIS.

    Returns
    -------
    bytes
        The FLVER file.
    """
    header = bytearray(tool.HEADER_SIZE)
    header[0:6] = b'FLVER\x00'
    header[6:8] = b'L\x00'
    struct.pack_into('<i', header, 8, 0x2001A)
    struct.pack_into('<3i', header, 20, 0, 0, len(nodes))
    header[tool.UNICODE_OFFSET] = 1 if unicode else 0
    names_at = tool.HEADER_SIZE + len(nodes) * tool.NODE_SIZE
    body = bytearray()
    names = bytearray()
    for name, parent, rotation, flags in nodes:
        node = bytearray(tool.NODE_SIZE)
        struct.pack_into('<i', node, 12, names_at + len(names))
        struct.pack_into('<3f', node, 16, *rotation)
        struct.pack_into('<h', node, 28, parent)
        struct.pack_into('<3f', node, 32, 1.0, 1.0, 1.0)
        struct.pack_into('<i', node, 60, flags)
        body += node
        names += (name.encode('utf-16-le') + b'\x00\x00') if unicode else (name.encode('shift_jis') + b'\x00')
    return bytes(header + body + names)


def close(a, b, tolerance=1e-6):
    """True when two quaternions are within ``tolerance`` per component."""
    return all(abs(x - y) <= tolerance for x, y in zip(a, b))


class ReadNodesTests(unittest.TestCase):

    def test_names_parents_and_flags(self):
        for unicode in (True, False):
            with self.subTest(unicode=unicode):
                nodes = tool.read_nodes(build_flver(unicode=unicode))
                self.assertEqual([n.name for n in nodes], [n[0] for n in NODES])
                self.assertEqual([n.parent for n in nodes], [n[1] for n in NODES])
                self.assertEqual([n.flags for n in nodes], [n[3] for n in NODES])

    def test_not_a_flver(self):
        with self.assertRaises(tool.FlverError):
            tool.read_nodes(b'NOTFLVER' + bytes(200))


class WorldOrientationTests(unittest.TestCase):

    def setUp(self):
        self.table = tool.world_orientations(tool.read_nodes(build_flver()))

    def test_rotations_follow_compute_local_transform(self):
        # Root: 90 degrees about Y; Child: Ry(90) then Rx(90), (0.5, 0.5, 0.5, -0.5)
        self.assertTrue(close(self.table['Root'], (ROOT_TO_HALF, 0.0, ROOT_TO_HALF, 0.0)))
        self.assertTrue(close(self.table['Child'], (0.5, 0.5, 0.5, -0.5)))

    def test_disabled_nodes_and_their_descendants_are_left_out(self):
        self.assertEqual(set(self.table), {'Root', 'Child'})

    def test_parent_past_the_list_is_refused(self):
        with self.assertRaises(tool.FlverError):
            tool.world_orientations(tool.read_nodes(build_flver([('A', 5, (0, 0, 0), 8)])))


class MergeTablesTests(unittest.TestCase):

    def test_first_file_wins_and_disagreement_is_reported(self):
        first = {'A': (1.0, 0.0, 0.0, 0.0)}
        turned = (math.cos(math.radians(5)), math.sin(math.radians(5)), 0.0, 0.0)  # 10 degrees
        table, disagreement = tool.merge_tables([first, {'A': turned, 'B': turned}])
        self.assertEqual(table['A'], first['A'])
        self.assertEqual(table['B'], turned)
        self.assertAlmostEqual(disagreement['A'], 10.0, places=6)

    def test_module_text_reads_back(self):
        table = {'B': (0.5, 0.5, 0.5, -0.5), 'A': (1.0, 0.0, 0.0, 0.0)}
        scope = {}
        exec(tool.render_module(table, ['x.flver']), scope)
        self.assertEqual(list(scope['ORIENTATIONS']), ['A', 'B'])
        self.assertTrue(close(scope['ORIENTATIONS']['B'], table['B']))


class TableTests(unittest.TestCase):

    def test_every_entry_is_a_unit_quaternion(self):
        self.assertGreater(len(vanilla_axes.ORIENTATIONS), 0)
        for name, q in vanilla_axes.ORIENTATIONS.items():
            self.assertEqual(len(q), 4, name)
            self.assertAlmostEqual(sum(c * c for c in q), 1.0, places=6, msg=name)

    def test_names_are_written_once(self):
        path = os.path.join(REPO_DIR, 'src', 'core', 'vanilla_axes.py')
        with open(path, encoding='utf-8') as handle:
            keys = [line.split(':')[0].strip() for line in handle if line.startswith("    '")]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(keys), len(vanilla_axes.ORIENTATIONS))


@unittest.skipUnless(os.path.exists(FC_F_0000) and os.path.isdir(IMPORTER_DIR),
                     "needs the game's FC_F_0000.flver and blender_flver_importer")
class CrossCheckTests(unittest.TestCase):
    """The tool's reader against another reader, on a real vanilla file."""

    def test_records_equal_blender_flver_importer(self):
        try:
            import bpy  # noqa: F401  (the importer's package imports bpy)
        except ImportError:
            self.skipTest("needs Blender")
        if IMPORTER_DIR not in sys.path:
            sys.path.insert(0, IMPORTER_DIR)
        from io_import_flver import flver_utils
        with open(FC_F_0000, 'rb') as handle:
            ours = tool.read_nodes(handle.read())
        theirs = flver_utils.read_flver(FC_F_0000).bones
        self.assertEqual(len(ours), len(theirs))
        for a, b in zip(ours, theirs):
            self.assertEqual((a.name, a.parent, a.flags), (b.name, b.parent_index, b.unk3C))
            self.assertTrue(close(a.rotation + a.scale, tuple(b.rotation) + tuple(b.scale), 1e-7))


if __name__ == '__main__':
    unittest.main()
