from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from package_release import package_release


class PublicReleaseTests(unittest.TestCase):
    def test_source_only_builder_runs_from_unpacked_zip(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            package = package_release(folder)
            first = package.read_bytes()
            self.assertEqual(package_release(folder).read_bytes(), first)
            with ZipFile(package) as archive:
                self.assertIsNone(archive.testzip())
                for name in archive.namelist():
                    path = Path(name)
                    self.assertEqual(path.parent.as_posix(), 'MHGU-Xbox-Builder')
                    self.assertTrue(path.name == 'README.md' or path.suffix == '.py')
                archive.extractall(folder)
            result = subprocess.run(
                [sys.executable, '-E', 'build_release.py', '--help'],
                cwd=folder / 'MHGU-Xbox-Builder', capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('--merge-mod', result.stdout)
