from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from build_help import build_help
from safe_paths import archive_name, within


class ResourcePathTests(unittest.TestCase):
    def test_arc_member_names(self):
        name = b'chS\\table\\example'
        self.assertEqual(archive_name(name.ljust(64, b'\0')), 'chS/table/example')
        for name in (b'', b'../one', b'chS\\table\\..\\one', b'/root/one',
                     b'C:\\one', b'chS/table/CON', b'chS/table/one:two',
                     b'chS/table/./one', b'one\0two', b'chS/table//one'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                archive_name(name)

    def test_symlinks_and_missing_children(self):
        with TemporaryDirectory() as temp:
            root = Path(temp).resolve() / 'romfs'
            root.mkdir()
            (root / 'local').symlink_to(root / 'assets', target_is_directory=True)
            self.assertEqual(within(root, 'local/text'), root / 'assets/text')
            (root / 'external').symlink_to(root.parent, target_is_directory=True)
            with self.assertRaises(ValueError):
                within(root, 'external/text')

    def test_help_requires_separate_input_and_output(self):
        with TemporaryDirectory() as temp:
            source = Path(temp) / 'game'
            source.mkdir()
            alias = Path(temp) / 'source-alias'
            alias.symlink_to(source, target_is_directory=True)
            for module in (source, source / 'mod', source.parent, alias / 'mod'):
                with self.subTest(module=module), self.assertRaisesRegex(ValueError, 'overlap'):
                    build_help(source, module, None)

    def test_help_rejects_external_output_romfs(self):
        with TemporaryDirectory() as temp:
            source, module = Path(temp) / 'game', Path(temp) / 'mod'
            source.mkdir()
            module.mkdir()
            (module / 'romfs').symlink_to(source, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'escapes'):
                build_help(source, module, None)
            self.assertEqual(list(source.iterdir()), [])
