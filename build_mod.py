"""Build Xbox keycaps for MHGU 1.4.0 from the two original Switch archives."""
import argparse
import io
from pathlib import Path
import struct
import zlib

from PIL import Image, ImageDraw, ImageFont
from build_probe import HEADER, MEMBER, block_offset

ARCHIVES = {
    'loc/arc/resident.arc': MEMBER,
    'chS/arc/quest_chS.arc': b'eng\\' + MEMBER,
}
# Cells are 24px square. First row of the original reads Y X B A.
KEYS = {
    (0, 0): 'X', (1, 0): 'Y', (2, 0): 'A', (3, 0): 'B',
    (4, 0): 'LB', (0, 1): 'RB', (5, 1): 'LT', (6, 1): 'RT',
    (7, 1): 'LS', (8, 1): 'RS', (0, 3): 'Menu', (1, 3): 'View',
}
COLORS = {'A': '#80d848', 'B': '#ff6363', 'X': '#60bbff', 'Y': '#ffdc53'}


def keycap(label, font):
    image = Image.new('RGBA', (96, 96))
    draw = ImageDraw.Draw(image)
    if label in ('LB', 'RB', 'LT', 'RT'):
        draw.rounded_rectangle((4, 13, 91, 82), 15, fill='#24282d', outline='white', width=5)
    else:
        draw.ellipse((4, 4, 91, 91), fill='#24282d', outline='white', width=5)
    if label == 'Menu':
        for y in (32, 48, 64):
            draw.line((27, y, 69, y), fill='white', width=6)
    elif label == 'View':
        draw.rectangle((24, 28, 58, 55), outline='white', width=5)
        draw.rectangle((38, 41, 72, 68), fill='#24282d', outline='white', width=5)
    else:
        face = ImageFont.truetype(str(font), 66 if len(label) == 1 else 43)
        draw.text((48, 48), label, font=face, anchor='mm', fill=COLORS.get(label, 'white'),
                  stroke_width=1)
    return image.resize((24, 24), Image.Resampling.LANCZOS)


def replace_texture(data, tiles):
    if len(data) != 65560 or data[:24] != HEADER:
        raise ValueError('Unexpected texture dimensions or layout')
    result = bytearray(data)
    for (col, row), tile in tiles.items():
        stream = io.BytesIO()
        tile.save(stream, 'DDS', pixel_format='DXT5')
        blocks = stream.getvalue()[128:]
        if len(blocks) != 576:
            raise ValueError('BC3 encoder returned unexpected block count')
        for y in range(6):
            for x in range(6):
                offset = block_offset(col * 6 + x, row * 6 + y)
                start = (y * 6 + x) * 16
                result[offset:offset + 16] = blocks[start:start + 16]
    return bytes(result)


WINDOW = b'GUI\\99_texture\\HD_window_BM_MQ_NOMIP'


PANEL = b'GUI\\99_texture\\HD_custom_pnl2_BM_NOMIP'
WINDOW_KEYS = [(48, 80, 'LB'), (80, 80, 'RB'), (0, 192, 'LT'), (32, 192, 'RT')]
# The four direction diagrams between RT and View each occupy another cell.
PANEL_KEYS = [(4 + 32 * i, 244, label) for i, label in
              enumerate(('LB', 'X', 'Y', 'A', 'B', 'RB', 'LT', 'RT'))]
PANEL_KEYS += [(388, 244, 'View'), (420, 244, 'Menu')]


def replace_ui_buttons(texture, font, cells):
    """Replace aligned 32px key cells in a 512px BC3 UI atlas."""
    if len(texture) != 262168 or texture[:24].hex() != '54455800a080002001800010011701000000040000000000':
        raise ValueError('Unexpected window texture layout')
    result = bytearray(texture)
    for left, top, label in cells:
        tile = Image.new('RGBA', (32, 32))
        tile.paste(keycap(label, font), (4, 4))
        stream = io.BytesIO()
        tile.save(stream, 'DDS', pixel_format='DXT5')
        blocks = stream.getvalue()[128:]
        if len(blocks) != 1024:
            raise ValueError('Unexpected BC3 tile size')
        for row in range(8):
            for col in range(8):
                x, y = left // 4 + col, top // 4 + row
                # 512px atlas uses 16 vertically stacked 512-byte Tegra GOBs.
                offset = (24 + x // 4 * 8192 + y // 8 * 512 + x % 4 // 2 * 256
                          + y % 8 // 2 * 64 + x % 2 * 32 + y % 2 * 16)
                start = (row * 8 + col) * 16
                result[offset:offset + 16] = blocks[start:start + 16]
    return bytes(result)


def replace_member(original, member, transform):
    arc = bytearray(original)
    magic, version, count = struct.unpack_from('<4sHH', arc)
    if magic != b'ARC\0' or version != 17:
        raise ValueError('Expected ARC version 17')
    record, = [p for p in range(12, 12 + count * 80, 80)
               if arc[p:p + 64].partition(b'\0')[0] == member]
    size, _, offset = struct.unpack_from('<III', arc, record + 68)
    texture = transform(zlib.decompress(arc[offset:offset + size]))
    packed = zlib.compress(texture, 9)
    if len(packed) > size:
        arc.extend(bytes(-len(arc) % 16))
        offset = len(arc)
    arc[offset:offset + len(packed)] = packed
    struct.pack_into('<I', arc, record + 68, len(packed))
    struct.pack_into('<I', arc, record + 76, offset)
    return arc


def patch_ui_archives(archive, font, window_prefix=b'', panel_prefix=b''):
    archive = replace_member(archive, window_prefix + WINDOW,
                             lambda texture: replace_ui_buttons(texture, font, WINDOW_KEYS))
    return replace_member(archive, panel_prefix + PANEL,
                          lambda texture: replace_ui_buttons(texture, font, PANEL_KEYS))


def patch_archive(original, member, tiles):
    return replace_member(original, member, lambda texture: replace_texture(texture, tiles))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('originals', type=Path, help='Directory containing original resident.arc and quest_chS.arc')
    parser.add_argument('module', type=Path)
    parser.add_argument('--font', type=Path, default='/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    args = parser.parse_args()
    tiles = {cell: keycap(label, args.font) for cell, label in KEYS.items()}
    for path, member in ARCHIVES.items():
        output = args.module / 'romfs/nativeNX' / path
        data = patch_archive((args.originals / Path(path).name).read_bytes(), member, tiles)
        if member == MEMBER:
            data = patch_ui_archives(data, args.font)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
