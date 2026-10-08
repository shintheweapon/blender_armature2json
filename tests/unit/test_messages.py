# Tests for core.messages (templates and ExportError); plain Python

import string
import unittest

from core import merge, messages


class ExportErrorTests(unittest.TestCase):

    def test_keeps_template_and_fields_and_formats_english(self):
        error = messages.ExportError(messages.NO_BONES, name='Rig')
        self.assertIsInstance(error, ValueError)
        self.assertEqual(error.template, messages.NO_BONES)
        self.assertEqual(error.fields, {'name': 'Rig'})
        self.assertEqual(str(error), "Armature 'Rig' has no bones.")

    def test_core_errors_carry_their_template(self):
        with self.assertRaises(messages.ExportError) as caught:
            merge.validate_input({'Name': 'Root'})
        self.assertEqual(caught.exception.template, messages.NOT_A_LIST)


class TemplateTests(unittest.TestCase):

    def test_templates_lists_every_constant(self):
        found = messages.templates()
        self.assertIn('NO_BONES', found)
        self.assertIn('MORE_IN_CONSOLE', found)
        self.assertTrue(all(isinstance(t, str) and t for t in found.values()))

    def test_templates_use_named_fields_only(self):
        for name, template in messages.templates().items():
            for _, field, _, _ in string.Formatter().parse(template):
                if field is not None:
                    self.assertTrue(field.isidentifier(), f'{name}: {{{field}}}')


if __name__ == '__main__':
    unittest.main()
