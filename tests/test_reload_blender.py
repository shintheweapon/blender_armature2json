# Reloading the add-on, as Blender does when it is reinstalled or re-enabled in
# a running session, must also reload its modules so their new code runs

import importlib
import unittest

import src
from src.core import writer
from src.operators import export_operator


class ReloadTests(unittest.TestCase):

    def test_reloading_the_package_reloads_its_modules(self):
        old_build = writer.build_nodes
        old_draw = export_operator.draw_options
        importlib.reload(src)
        self.assertIsNot(src.core.writer.build_nodes, old_build)
        self.assertIsNot(src.operators.export_operator.draw_options, old_draw)


if __name__ == '__main__':
    unittest.main()
