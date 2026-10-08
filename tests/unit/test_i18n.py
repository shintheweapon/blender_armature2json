# Tests for core.i18n_zh_hans (completeness and placeholders); plain Python

import string
import unittest

from core import i18n_zh_hans, messages


def fields(text):
    """The named fields of a format string, sorted."""
    return sorted(name for _, name, _, _ in string.Formatter().parse(text) if name)


class TableTests(unittest.TestCase):

    def setUp(self):
        self.table = i18n_zh_hans.table()

    def test_every_message_template_is_translated(self):
        missing = [name for name, template in messages.templates().items()
                   if (i18n_zh_hans.DEFAULT, template) not in self.table]
        self.assertEqual(missing, [])

    def test_translations_keep_the_same_fields(self):
        for (_, english), chinese in self.table.items():
            self.assertEqual(fields(english), fields(chinese), english)

    def test_no_entry_is_empty_or_untranslated(self):
        for (_, english), chinese in self.table.items():
            self.assertTrue(chinese.strip(), english)
            self.assertNotEqual(chinese, english)

    def test_keys_are_context_and_text_pairs(self):
        for key in self.table:
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 2)
            self.assertIn(key[0], (i18n_zh_hans.DEFAULT, i18n_zh_hans.OPERATOR))

    def test_operator_texts_in_both_contexts(self):
        for english in ("Export FLVER Nodes JSON", "FLVER Nodes JSON (.json)"):
            self.assertIn((i18n_zh_hans.DEFAULT, english), self.table)
            self.assertIn((i18n_zh_hans.OPERATOR, english), self.table)

    def test_every_axis_item_is_translated(self):
        for axis in ('X', 'Y', 'Z', '-X', '-Y', '-Z'):
            self.assertEqual(self.table[(i18n_zh_hans.DEFAULT, f"Node {axis} axis")],
                             f"节点 {axis} 轴")


if __name__ == '__main__':
    unittest.main()
