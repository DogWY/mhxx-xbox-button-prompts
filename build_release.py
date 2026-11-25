"""Generate an installable MHGU Xbox prompt mod from a local 1.4.0 RomFS."""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from build_help import build_help
from build_mod import KEYS, MEMBER, keycap, patch_archive, patch_ui_archives
from build_title import TEXTURE, patch_title, patch_title_archive
from merge_mods import merge_mods
from safe_paths import require_disjoint, within


def build(romfs, output, font, mods=()):
    romfs = romfs.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError(f'Choose a new output directory: {output}')
    mods = [mod.resolve(strict=True) for mod in mods]
    for source in [romfs, *mods]:
        require_disjoint(source, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.mhgu-', dir=output.parent) as temp:
        module = Path(temp) / 'module'
        native = within(romfs, 'nativeNX')
        target = module / 'romfs/nativeNX'
        resident = Path('loc/arc/resident.arc')
        tiles = {cell: keycap(label, font) for cell, label in KEYS.items()}
        archive = patch_archive(within(native, resident).read_bytes(), MEMBER, tiles)
        (target / resident).parent.mkdir(parents=True)
        (target / resident).write_bytes(patch_ui_archives(archive, font))

        build_help(romfs, module, font)
        title = Path('chS/arc/title_chS.arc')
        (target / title).write_bytes(patch_title_archive(within(native, title).read_bytes(), font))
        (target / TEXTURE).parent.mkdir(parents=True, exist_ok=True)
        (target / TEXTURE).write_bytes(patch_title(within(native, TEXTURE).read_bytes(), font))
        merge_mods(romfs, module / 'romfs', mods)
        module.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('romfs', type=Path, help='Dumped RomFS containing nativeNX')
    parser.add_argument('output', type=Path, nargs='?', default=Path('0.MHGU-Xbox-Button-Prompts'))
    parser.add_argument('--font', type=Path, default=Path('/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
    parser.add_argument('--merge-mod', action='append', default=[], type=Path, metavar='MOD',
                        help='Combine changes from a local mod containing romfs/ (repeatable)')
    args = parser.parse_args()
    build(args.romfs, args.output, args.font, args.merge_mod)
