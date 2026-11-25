"""Update literal controller names in MHGU Simplified Chinese help resources."""
import argparse
from pathlib import Path
import re
import struct
from tempfile import TemporaryDirectory
import zlib

from build_mod import ARCHIVES as BUTTON_ARCHIVES
from build_mod import KEYS, keycap, patch_archive, patch_ui_archives, replace_texture
from safe_paths import archive_name, require_disjoint, within

ARCHIVES = ('resident_chS.arc', 'result_chS.arc', 'village/common_chS.arc',
            'village/hunter_note_chS.arc', 'tutorial/common_chS.arc',
            'npc/npcFakeArc_chS.arc', 'quest_chS.arc')
BUTTON = {'A': 'B', 'B': 'A', 'X': 'Y', 'Y': 'X',
          'L': 'LB', 'R': 'RB', 'ZL': 'LT', 'ZR': 'RT'}
# One trailing 键/按钮 can qualify an entire chord or list of alternatives.
KEY = r'(?:Z[LR]|[ABXYLR])'
BUTTON_GROUP = re.compile(rf'(?<![a-zA-Z0-9_]){KEY}(?:[+＋、或和与/／]{KEY})*(?=键|按钮)')


def update_gmd(gmd):
    if gmd[:8] != bytes.fromhex('474d440002030100'):
        return gmd
    size, = struct.unpack_from('<I', gmd, 32)
    if not size:
        return gmd
    if size > len(gmd) - 40:
        raise ValueError('Invalid GMD text size')
    text = gmd[-size:].decode('utf-8')
    updated = BUTTON_GROUP.sub(lambda m: re.sub(KEY, lambda b: BUTTON[b[0]], m[0]), text)
    if updated == text:
        return gmd
    body = updated.encode('utf-8')
    header = bytearray(gmd[:-size])
    struct.pack_into('<I', header, 32, len(body))
    return header + body


def build_help(romfs, module, font):
    require_disjoint(romfs, module)
    destination = within(module, 'romfs')
    outputs = {}
    tiles = {cell: keycap(label, font) for cell, label in KEYS.items()}
    for name in ARCHIVES:
        rel = Path('nativeNX/chS/arc') / name
        arc = bytearray(within(romfs, rel).read_bytes())
        if arc[:6] != b'ARC\0\x11\0':
            raise ValueError(f'Unknown ARC format in {name}')
        changes = 0
        for p in range(12, 12 + 80 * int.from_bytes(arc[6:8], 'little'), 80):
            member = archive_name(bytes(arc[p:p+64]))
            if not member.startswith('chS/table/'):
                continue
            size, flags_size, offset = struct.unpack_from('<III', arc, p + 68)
            old = zlib.decompress(arc[offset:offset+size])
            new = update_gmd(old)
            if new == old:
                continue
            if flags_size & 0x1fffffff != len(old):
                raise ValueError(f'Invalid member size for {member}')
            compressed = zlib.compress(new, 9)
            arc.extend(bytes(-len(arc) % 16))
            struct.pack_into('<III', arc, p + 68, len(compressed),
                             flags_size & 0xe0000000 | len(new), len(arc))
            arc.extend(compressed)
            loose = Path('nativeNX') / (member + '.gmd')
            loose_input = within(romfs, loose)
            if loose_input.is_file():
                loose_old = loose_input.read_bytes()
                loose_new = update_gmd(loose_old)
                if loose_new != loose_old:
                    outputs[loose] = loose_new
            changes += 1
        if name == 'resident_chS.arc':
            arc = patch_ui_archives(arc, font, b'chS\\', b'eng\\')
        if name == 'quest_chS.arc':
            arc = patch_archive(arc, BUTTON_ARCHIVES['chS/arc/quest_chS.arc'], tiles)
        if changes or name in ('resident_chS.arc', 'quest_chS.arc'):
            outputs[rel] = arc
        print(name, changes)
    rel = Path('nativeNX/eng/GUI/02_common/font/button_festa_00_ID.tex')
    outputs[rel] = replace_texture(within(romfs, rel).read_bytes(), tiles)
    # Validate every destination before modifying a module from an earlier build.
    targets = [(within(destination, rel), data) for rel, data in outputs.items()]
    for target, data in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=target.parent) as temp:
            pending = Path(temp) / 'resource'
            pending.write_bytes(data)
            pending.replace(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('romfs', type=Path)
    parser.add_argument('module', type=Path)
    parser.add_argument('--font', default='/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    args = parser.parse_args()
    build_help(args.romfs, args.module, args.font)
