"""Replace the baked Switch A in the MHGU title screen's PRESS A texture."""
import argparse
import hashlib
import io
import struct
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TEXTURE = Path('eng/GUI/99_texture/HD_title00_BM_NOMIP.tex')


def patch_title(original, font):
    if hashlib.sha256(original).hexdigest() != '070fb6c551eeacf325550fd8acaa9c98d588d9f2869f998853e849589d36c3da':
        raise ValueError('Unsupported title atlas')
    # This 52-by-52 circle is separate from the PRESS lettering. The
    # surrounding transparent texels also belong to this sprite.
    icon = Image.new('RGBA', (56 * 4, 56 * 4))
    draw = ImageDraw.Draw(icon)
    draw.ellipse((8, 8, 215, 215), fill='#24282d', outline='white', width=8)
    face = ImageFont.truetype(str(font), 154)
    draw.text((112, 112), 'B', font=face, fill='#ff6363', anchor='mm')
    stream = io.BytesIO()
    icon.resize((56, 56), Image.Resampling.LANCZOS).save(stream, 'DDS', pixel_format='DXT5')
    blocks = stream.getvalue()[128:]
    if len(blocks) != 14 * 14 * 16:
        raise ValueError('Unexpected BC3 block count')
    result = bytearray(original)
    for row in range(14):
        for col in range(14):
            x, y = 63 + col, 175 + row  # top left is pixel (252, 700)
            # Tegra block-linear, 16 GOBs high, 1024px wide, BC3.
            pos = (24 + y // 128 * 524288 + x // 4 * 8192
                   + (y % 128) // 8 * 512 + x % 4 // 2 * 256
                   + y % 8 // 2 * 64 + x % 2 * 32 + y % 2 * 16)
            src = (row * 14 + col) * 16
            result[pos:pos + 16] = blocks[src:src + 16]
    return bytes(result)


def patch_title_archive(source, font):
    data = bytearray(source)
    magic, version, count = struct.unpack_from('<4sHH', data)
    if magic != b'ARC\0' or version != 17:
        raise ValueError('Expected MHGU ARC v17')
    member = str(TEXTURE.with_suffix('')).replace('/', chr(92)).encode()
    record, = [p for p in range(12, 12 + 80 * count, 80)
               if data[p:p + 64].partition(b'\0')[0] == member]
    size, _, offset = struct.unpack_from('<III', data, record + 68)
    packed = zlib.compress(patch_title(zlib.decompress(data[offset:offset + size]), font), 9)
    if len(packed) > size:
        data.extend(bytes(-len(data) % 16))
        offset = len(data)
    data[offset:offset + len(packed)] = packed
    struct.pack_into('<I', data, record + 68, len(packed))
    struct.pack_into('<I', data, record + 76, offset)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_root', type=Path)
    parser.add_argument('module', type=Path)
    parser.add_argument('--font', type=Path, default='/System/Library/Fonts/Supplemental/Arial Bold.ttf')
    parser.add_argument('--title-archive', type=Path, help='Use an existing title mod as the base')
    args = parser.parse_args()
    output = args.module / 'romfs/nativeNX' / TEXTURE
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(patch_title((args.native_root / TEXTURE).read_bytes(), args.font))
    archive = Path('chS/arc/title_chS.arc')
    target = args.module / 'romfs/nativeNX' / archive
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(patch_title_archive((args.title_archive or args.native_root / archive).read_bytes(), args.font))
