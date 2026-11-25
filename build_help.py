"""Update literal controller names in MHGU Simplified Chinese help resources."""
import argparse
from pathlib import Path
import re
import struct
import zlib

from build_mod import ARCHIVES as BUTTON_ARCHIVES
from build_mod import KEYS, keycap, patch_archive, patch_ui_archives, replace_texture

ARCHIVES = ('resident_chS.arc', 'result_chS.arc', 'village/common_chS.arc',
            'village/hunter_note_chS.arc', 'tutorial/common_chS.arc',
            'npc/npcFakeArc_chS.arc', 'quest_chS.arc')
BUTTON = {'A': 'B', 'B': 'A', 'X': 'Y', 'Y': 'X',
          'L': 'LB', 'R': 'RB', 'ZL': 'LT', 'ZR': 'RT'}
# Only match a key or chord explicitly identified as a button in Chinese.
KEY = r'(?:Z[LR]|[ABXYLR])'
CHORD = re.compile(r'(?<![a-zA-Z0-9_])' + KEY + r'(?:[+＋]' + KEY + r')*(?=键|按钮)')


def update_gmd(gmd):
    if gmd[:8] != bytes.fromhex('474d440002030100'):
        return gmd
    size, = struct.unpack_from('<I', gmd, 32)
    if not size:
        return gmd
    if size > len(gmd) - 40:
        raise ValueError('Invalid GMD text size')
    text = gmd[-size:].decode('utf-8')
    updated = CHORD.sub(lambda m: re.sub(KEY, lambda b: BUTTON[b[0]], m[0]), text)
    if updated == text:
        return gmd
    body = updated.encode('utf-8')
    header = bytearray(gmd[:-size])
    struct.pack_into('<I', header, 32, len(body))
    return header + body


def build_help(romfs, module, font):
    destination = module / 'romfs'
    tiles = {cell: keycap(label, font) for cell, label in KEYS.items()}
    for name in ARCHIVES:
        rel = Path('nativeNX/chS/arc') / name
        arc = bytearray((romfs / rel).read_bytes())
        if arc[:6] != b'ARC\0\x11\0':
            raise ValueError(f'Unknown ARC format in {name}')
        changes = 0
        for p in range(12, 12 + 80 * int.from_bytes(arc[6:8], 'little'), 80):
            member = bytes(arc[p:p+64]).partition(b'\0')[0].decode().replace('\\','/')
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
            if (romfs / loose).is_file():
                loose_new = update_gmd((romfs / loose).read_bytes())
                if loose_new != (romfs / loose).read_bytes():
                    (destination / loose).parent.mkdir(parents=True, exist_ok=True)
                    (destination / loose).write_bytes(loose_new)
            changes += 1
        if name == 'resident_chS.arc':
            arc = patch_ui_archives(arc, font, b'chS\\', b'eng\\')
        if name == 'quest_chS.arc':
            arc = patch_archive(arc, BUTTON_ARCHIVES['chS/arc/quest_chS.arc'], tiles)
        if changes or name in ('resident_chS.arc', 'quest_chS.arc'):
            (destination / rel).parent.mkdir(parents=True, exist_ok=True)
            (destination / rel).write_bytes(arc)
        print(name, changes)
    rel = Path('nativeNX/eng/GUI/02_common/font/button_festa_00_ID.tex')
    (destination / rel).parent.mkdir(parents=True, exist_ok=True)
    (destination / rel).write_bytes(replace_texture((romfs / rel).read_bytes(), tiles))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('romfs', type=Path)
    parser.add_argument('module', type=Path)
    parser.add_argument('--font', default='/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    args = parser.parse_args()
    build_help(args.romfs, args.module, args.font)
