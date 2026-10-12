# Tests for core.files (same-file detection, atomic writes); plain Python

import os
import tempfile
import unittest
from unittest import mock

from core import files


class SameFileTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.dir = self.folder.name
        self.a = os.path.join(self.dir, 'input.json')
        self.b = os.path.join(self.dir, 'other.json')
        for path in (self.a, self.b):
            with open(path, 'w', encoding='utf-8') as handle:
                handle.write('[]')

    def tearDown(self):
        self.folder.cleanup()

    def test_same_path(self):
        self.assertTrue(files.same_file(self.a, self.a))

    def test_relative_and_absolute(self):
        previous = os.getcwd()
        os.chdir(self.dir)
        try:
            self.assertTrue(files.same_file('input.json', self.a))
            self.assertTrue(files.same_file(os.path.join('.', 'sub', '..', 'input.json'), self.a))
        finally:
            os.chdir(previous)

    @unittest.skipUnless(os.name == 'nt', 'letter case only folds on Windows')
    def test_other_letter_case(self):
        self.assertTrue(files.same_file(self.a.upper(), self.a))

    def test_hard_link(self):
        link = os.path.join(self.dir, 'link.json')
        os.link(self.a, link)
        self.assertTrue(files.same_file(link, self.a))

    def test_different_files(self):
        self.assertFalse(files.same_file(self.a, self.b))

    def test_path_that_does_not_exist_yet(self):
        new = os.path.join(self.dir, 'new.json')
        self.assertFalse(files.same_file(new, self.a))
        self.assertTrue(files.same_file(new, os.path.join(self.dir, '.', 'new.json')))


class WriteTextAtomicTests(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, 'out.json')

    def tearDown(self):
        self.folder.cleanup()

    def read(self):
        with open(self.path, 'rb') as handle:
            return handle.read()

    def test_writes_utf8_without_newline_translation(self):
        files.write_text_atomic(self.path, '[1,\n"é"]')
        self.assertEqual(self.read(), '[1,\n"é"]'.encode('utf-8'))
        self.assertEqual(os.listdir(self.folder.name), ['out.json'])

    def test_replaces_existing_file(self):
        files.write_text_atomic(self.path, 'old')
        files.write_text_atomic(self.path, 'new')
        self.assertEqual(self.read(), b'new')
        self.assertEqual(os.listdir(self.folder.name), ['out.json'])

    def test_failed_write_keeps_old_file_and_leaves_no_temp(self):
        files.write_text_atomic(self.path, 'good')
        real = tempfile.NamedTemporaryFile

        def failing(*args, **kwargs):
            handle = real(*args, **kwargs)
            handle.write = mock.Mock(side_effect=OSError('disk full'))
            return handle

        with mock.patch.object(files.tempfile, 'NamedTemporaryFile', failing):
            with self.assertRaisesRegex(OSError, 'disk full'):
                files.write_text_atomic(self.path, 'bad')
        self.assertEqual(self.read(), b'good')
        self.assertEqual(os.listdir(self.folder.name), ['out.json'])

    def test_failed_replace_keeps_old_file_and_leaves_no_temp(self):
        files.write_text_atomic(self.path, 'good')
        with mock.patch.object(files.os, 'replace', side_effect=PermissionError('in use')):
            with self.assertRaises(PermissionError):
                files.write_text_atomic(self.path, 'bad')
        self.assertEqual(self.read(), b'good')
        self.assertEqual(os.listdir(self.folder.name), ['out.json'])


if __name__ == '__main__':
    unittest.main()
