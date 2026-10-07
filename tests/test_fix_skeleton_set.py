# Tests for tools/fix_skeleton_set.py; run in the Blender suite or with plain Python

import contextlib
import io
import os
import struct
import sys
import tempfile
import unittest

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)

from tools import fix_skeleton_set as fix  # noqa: E402

# Parent per node: 0 root with children 1 and 3; 1 has child 2; 4 is a second root
PARENTS = [-1, 0, 1, 0, -1]
LINKS = [  # (parent, first child, next sibling, previous sibling)
    (-1, 1, 4, -1),
    (0, 2, 3, -1),
    (1, -1, -1, -1),
    (0, -1, -1, 1),
    (-1, -1, -1, 0),
]
TAIL = b'TAIL-DATA-AFTER-SKELETON'


def build_flver(links=LINKS, skeleton=None, version=fix.MIN_VERSION,
                endian=b'L\x00', base_count=None, all_count=None):
    """
    Build a minimal FLVER: header, nodes and a SkeletonSet, nothing else.

    Parameters
    ----------
    links : list of tuple
        Node links (parent, first child, next sibling, previous sibling).
    skeleton : list of tuple, optional
        SkeletonSet entries (parent, first, next, previous, NodeIndex) for
        both halves; defaults to deliberately wrong entries.
    version : int
        FLVER version field.
    endian : bytes
        Two-byte endian marker.
    base_count, all_count : int, optional
        Override the stored half sizes.

    Returns
    -------
    bytes
        The FLVER file.
    """
    count = len(links)
    if skeleton is None:
        skeleton = [(-1, -1, -1, -1, count - 1 - i) for i in range(count)]
    header = bytearray(fix.HEADER_SIZE)
    header[0:6] = b'FLVER\x00'
    header[6:8] = endian
    struct.pack_into('<i', header, 8, version)
    struct.pack_into('<5i', header, 20, 0, 0, count, 0, 0)
    nodes = bytearray()
    for parent, first, nxt, prev in links:
        node = bytearray(fix.NODE_SIZE)
        struct.pack_into('<hh', node, 28, parent, first)
        struct.pack_into('<hh', node, 44, nxt, prev)
        nodes += node
    skeleton_offset = fix.HEADER_SIZE + len(nodes)
    base_offset = skeleton_offset + fix.SKELETON_HEADER_SIZE
    all_offset = base_offset + count * fix.SKELETON_ENTRY_SIZE
    sk_header = struct.pack('<hhII', count if base_count is None else base_count,
                            count if all_count is None else all_count,
                            base_offset, all_offset) + bytes(20)
    entries = b''.join(struct.pack('<hhhhii', *entry, 0) for entry in skeleton)
    return bytes(header + nodes) + sk_header + entries + entries + TAIL


def mirrored(links=LINKS):
    """SkeletonSet entries that mirror ``links``."""
    return [tuple(link) + (index,) for index, link in enumerate(links)]


class RebuildTests(unittest.TestCase):

    def fix(self, data):
        layout = fix.read_layout(data)
        return layout, fix.rebuild_skeleton_set(data, layout, fix.read_nodes(data, layout))

    def test_every_entry_mirrors_its_node_after_the_fix(self):
        data = build_flver()
        layout, fixed = self.fix(data)
        self.assertEqual(fix.mirrored_entries(data, layout, fix.read_nodes(data, layout)),
                         {'base': 0, 'all': 0})
        nodes = fix.read_nodes(fixed, layout)
        self.assertEqual(fix.mirrored_entries(fixed, layout, nodes),
                         {'base': len(LINKS), 'all': len(LINKS)})

    def test_only_skeleton_entries_change(self):
        data = build_flver()
        layout, fixed = self.fix(data)
        start = layout.base_offset
        end = layout.all_offset + layout.all_count * fix.SKELETON_ENTRY_SIZE
        self.assertEqual(len(fixed), len(data))
        self.assertEqual(fixed[:start], data[:start])
        self.assertEqual(fixed[end:], data[end:])
        self.assertTrue(fixed.endswith(TAIL))

    def test_already_mirrored_file_is_byte_identical(self):
        data = build_flver(skeleton=mirrored())
        _, fixed = self.fix(data)
        self.assertEqual(fixed, data)


class RefusalTests(unittest.TestCase):

    def assert_refused(self, data):
        with self.assertRaises(fix.FlverError):
            layout = fix.read_layout(data)
            fix.rebuild_skeleton_set(data, layout, fix.read_nodes(data, layout))

    def test_big_endian_refused(self):
        self.assert_refused(build_flver(endian=b'B\x00'))

    def test_old_version_refused(self):
        self.assert_refused(build_flver(version=0x20014))

    def test_count_mismatch_refused(self):
        self.assert_refused(build_flver(base_count=len(LINKS) - 1))

    def test_inconsistent_node_links_refused(self):
        broken = list(LINKS)
        broken[0] = (-1, 3, 4, -1)  # first child should be 1
        self.assert_refused(build_flver(links=broken))


class CommandLineTests(unittest.TestCase):

    def run_main(self, args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = fix.main(args)
        return code, out.getvalue()

    def test_writes_default_copy_and_keeps_input(self):
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, 'model.flver')
            data = build_flver()
            with open(source, 'wb') as handle:
                handle.write(data)
            code, text = self.run_main([source])
            self.assertEqual(code, 0, text)
            target = os.path.join(folder, 'model.skelfix.flver')
            with open(source, 'rb') as handle:
                self.assertEqual(handle.read(), data)
            with open(target, 'rb') as handle:
                fixed = handle.read()
            layout = fix.read_layout(fixed)
            self.assertEqual(fix.mirrored_entries(fixed, layout, fix.read_nodes(fixed, layout)),
                             {'base': len(LINKS), 'all': len(LINKS)})

    def test_existing_output_and_same_path_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            source = os.path.join(folder, 'model.flver')
            target = os.path.join(folder, 'taken.flver')
            for path in (source, target):
                with open(path, 'wb') as handle:
                    handle.write(build_flver())
            self.assertEqual(self.run_main([source, target])[0], 1)
            self.assertEqual(self.run_main([source, source])[0], 1)
            with open(target, 'rb') as handle:
                self.assertEqual(handle.read(), build_flver())


if __name__ == '__main__':
    unittest.main()
