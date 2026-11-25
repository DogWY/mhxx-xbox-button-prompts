"""Build a single-glyph MHGU LayeredFS probe from a resident.arc dump."""
import argparse
from pathlib import Path
import struct
import zlib


MEMBER = b"GUI\\02_common\\font\\button_festa_00_ID"
HEADER = bytes.fromhex("54455800a080002001400008011701000000010000000000")


def block_offset(x, y):
    """Byte address of a BC3 block in the 256px Tegra block-linear atlas."""
    byte_x = x * 16
    return (24 + (y // 64) * 65536 + (byte_x // 64) * 4096
            + ((y % 64) // 8) * 512 + ((byte_x % 64) // 32) * 256
            + ((y % 8) // 2) * 64 + ((byte_x % 32) // 16) * 32
            + (y % 2) * 16)


def build_probe(source, destination):
    arc = bytearray(source.read_bytes())
    magic, version, count = struct.unpack_from("<4sHH", arc)
    if magic != b"ARC\0" or version != 17 or len(arc) < 12 + 80 * count:
        raise ValueError("Expected a Switch MHGU v17 ARC")
    matches = [p for p in range(12, 12 + 80 * count, 80)
               if arc[p:p + 64].partition(b"\0")[0] == MEMBER]
    if len(matches) != 1:
        raise ValueError("Expected exactly one button atlas")
    record = matches[0]
    size, _, offset = struct.unpack_from("<III", arc, record + 68)
    texture = bytearray(zlib.decompress(arc[offset:offset + size]))
    if len(texture) != 65560 or texture[:24] != HEADER:
        raise ValueError("Unsupported button atlas layout")
    # The Switch A glyph occupies the fourth 24px cell in the first row.
    # Change only its central 8x8 pixels to opaque magenta.
    magenta = bytes.fromhex("ffff0000000000001ff81ff800000000")
    for y in (2, 3):
        for x in (20, 21):
            p = block_offset(x, y)
            texture[p:p + 16] = magenta
    packed = zlib.compress(texture, 9)
    if len(packed) <= size:
        arc[offset:offset + len(packed)] = packed
    else:
        arc.extend(bytes(-len(arc) % 16))
        offset = len(arc)
        arc.extend(packed)
    struct.pack_into("<I", arc, record + 68, len(packed))
    struct.pack_into("<I", arc, record + 76, offset)
    if zlib.decompress(arc[offset:offset + len(packed)]) != texture:
        raise ValueError("Repacked atlas failed verification")
    if destination.resolve() == source.resolve():
        raise ValueError("Choose a separate output file")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(arc)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    build_probe(args.source, args.destination)
