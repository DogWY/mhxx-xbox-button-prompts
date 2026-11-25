"""Merge other mods' changes into overlapping files in a staged MHGU RomFS."""
from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import zlib

from safe_paths import archive_name, require_disjoint, within


HEADER = struct.Struct('<4sHHI')
RECORD = struct.Struct('<64sIIII')
SIZE_MASK = 0x1fffffff


@dataclass(frozen=True)
class Member:
    # The game looks up the name and type stored in the dictionary key. Compare
    # the remaining metadata and decoded content, independent of zlib settings.
    flags_size: int
    digest: bytes
    packed: bytes = field(compare=False)
    raw_name: bytes = field(compare=False)


def read_members(data, label):
    if len(data) < HEADER.size:
        raise ValueError(f'{label}: truncated ARC header')
    magic, version, count, reserved = HEADER.unpack_from(data)
    end = HEADER.size + count * RECORD.size
    if (magic, version, reserved) != (b'ARC\0', 17, 0) or end > len(data):
        raise ValueError(f'{label}: unsupported or truncated ARC v17')
    members = {}
    for pos in range(HEADER.size, end, RECORD.size):
        raw_name, kind, length, flags_size, offset = RECORD.unpack_from(data, pos)
        name = archive_name(raw_name)
        key = (name, kind)
        if key in members or offset < end or length > len(data) - offset:
            raise ValueError(f'{label}: invalid or duplicate ARC record {name!r}')
        packed = data[offset:offset + length]
        decoder = zlib.decompressobj()
        size = flags_size & SIZE_MASK
        try:
            raw = decoder.decompress(packed, size + 1)
        except zlib.error as exc:
            raise ValueError(f'{label}: invalid compressed member {name!r}') from exc
        if len(raw) != size or not decoder.eof or decoder.unused_data:
            raise ValueError(f'{label}: invalid ARC member length for {name!r}')
        members[key] = Member(flags_size, hashlib.sha256(raw).digest(), packed, raw_name)
    return members


def write_members(members):
    table_size = HEADER.size + len(members) * RECORD.size
    # The unmodified Switch archives start their data on a 32 KiB boundary.
    data = bytearray((table_size + 0x7fff) & ~0x7fff)
    HEADER.pack_into(data, 0, b'ARC\0', 17, len(members), 0)
    for index, ((_, kind), member) in enumerate(members.items()):
        RECORD.pack_into(data, HEADER.size + index * RECORD.size, member.raw_name, kind,
                         len(member.packed), member.flags_size, len(data))
        data.extend(member.packed)
    return bytes(data)


def merge_archive(stock, built, incoming, relative):
    original = read_members(stock, relative)
    result = read_members(built, relative)
    changed = False
    for source, data in incoming:
        incoming_members = read_members(data, source)
        # Preserve existing record order and append new names in source order.
        for key in dict.fromkeys([*original, *incoming_members]):
            old = original.get(key)
            new = incoming_members.get(key)
            current = result.get(key)
            if new == old or new == current:
                continue
            if current != old:
                name, kind = key
                raise ValueError(f'{source}: conflicting changes to {relative}, '
                                 f'member {name!r} (type {kind:#x})')
            if new is None:
                del result[key]
            else:
                result[key] = new
            changed = True
    return write_members(result) if changed else built


def merge_mods(stock_romfs, built_romfs, mods):
    """Apply disjoint changes to the files produced by the Xbox builder."""
    if not mods:
        return
    roots = []
    require_disjoint(stock_romfs, built_romfs)
    for mod in mods:
        root = within(mod, Path('romfs'))
        if not root.is_dir():
            raise ValueError(f'Expected a mod directory containing romfs: {mod}')
        require_disjoint(root, built_romfs)
        roots.append(root)

    changes = {}
    for target in sorted(built_romfs.rglob('*')):
        if target.is_symlink():
            raise ValueError(f'Unexpected symlink in builder output: {target}')
        if not target.is_file():
            continue
        relative = target.relative_to(built_romfs)
        candidates = [within(root, relative) for root in roots]
        incoming = [(path, path.read_bytes()) for path in candidates if path.exists()]
        if not incoming:
            continue
        stock = within(stock_romfs, relative).read_bytes()
        built = target.read_bytes()
        if relative.suffix.lower() == '.arc':
            merged = merge_archive(stock, built, incoming, relative)
        else:
            merged = built
            for path, data in incoming:
                if data == stock or data == merged:
                    continue
                if merged != stock:
                    raise ValueError(f'{path}: conflicting changes to {relative}')
                merged = data
        if merged != built:
            changes[target] = merged

    # Check all conflicts before writing; replacing also avoids writing
    # through a pre-existing hard link. The caller owns the staging tree.
    for target, data in changes.items():
        with TemporaryDirectory(dir=target.parent) as temp:
            pending = Path(temp) / target.name
            pending.write_bytes(data)
            pending.replace(target)
