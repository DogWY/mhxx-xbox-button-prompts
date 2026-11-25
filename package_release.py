"""Package the local MHGU mod builder for distribution."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PACKAGE = 'MHGU-Xbox-Builder'
SOURCE = Path(__file__).resolve().parent
FILES = (
    'README.md',
    'build_release.py',
    'build_help.py',
    'build_mod.py',
    'build_probe.py',
    'build_title.py',
    'merge_mods.py',
    'safe_paths.py',
)


def package_release(destination):
    destination.mkdir(parents=True, exist_ok=True)
    archive = destination / (PACKAGE + '.zip')
    with TemporaryDirectory(dir=destination) as staging:
        pending = Path(staging) / archive.name
        with ZipFile(pending, 'w') as bundle:
            for name in FILES:
                path = SOURCE / name
                if path.is_symlink() or not path.is_file():
                    raise ValueError(f'Expected a regular source file: {name}')
                entry = ZipInfo(f'{PACKAGE}/{name}')
                entry.create_system = 3
                entry.external_attr = 0o100644 << 16
                bundle.writestr(entry, path.read_bytes(), compress_type=ZIP_DEFLATED)
        pending.replace(archive)
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, nargs='?', default=Path.cwd(),
                        help='Output directory (default: current directory)')
    print(package_release(parser.parse_args().destination))
