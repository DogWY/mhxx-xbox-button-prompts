from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest
import zlib

from merge_mods import merge_mods


def archive(members, level=6):
    data = bytearray(12 + 80 * len(members))
    struct.pack_into('<4sHHI', data, 0, b'ARC\0', 17, len(members), 0)
    for i, ((name, kind), value) in enumerate(members.items()):
        packed = zlib.compress(value, level)
        struct.pack_into('<64sIIII', data, 12 + i * 80, name.encode(), kind,
                         len(packed), 0x40000000 | len(value), len(data))
        data.extend(packed)
    return bytes(data)


def contents(data):
    count, = struct.unpack_from('<H', data, 6)
    result = {}
    for i in range(count):
        name, kind, size, flags_size, offset = struct.unpack_from('<64sIIII', data, 12 + 80 * i)
        raw = zlib.decompress(data[offset:offset + size])
        assert len(raw) == (flags_size & 0x1fffffff)
        result[name.rstrip(b'\0').decode(), kind] = raw
    return result


class MergeModTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stock = self.root / 'stock'
        self.built = self.root / 'built'
        self.mods = [self.root / 'one', self.root / 'two']
        for folder in [self.stock, self.built, *(mod / 'romfs' for mod in self.mods)]:
            folder.mkdir(parents=True)

    def test_independent_edits_adds_deletes_and_recompressed_identical_edits(self):
        base = {('gui', 1): b'base', ('gui', 2): b'other type', ('music', 3): b'SFX',
                ('obsolete', 4): b'old'}
        ours = {**base, ('gui', 1): b'Xbox', ('atlas', 1): b'new'}
        theirs = {**base, ('gui', 2): b'HD', ('extra', 5): b'added'}
        del theirs['obsolete', 4]
        second = {**base, ('gui', 1): b'Xbox', ('music', 3): b'new audio'}
        paths = [root / 'shared.arc' for root in
                 [self.stock, self.built, *(m / 'romfs' for m in self.mods)]]
        for n, (path, members) in enumerate(zip(paths, [base, ours, theirs, second])):
            path.write_bytes(archive(members, level=1 + n))
        (self.mods[0] / 'romfs/unrelated.bin').write_bytes(b'owned by other mod')
        snapshots = {p: p.read_bytes() for p in [paths[0], *paths[2:]]}

        merge_mods(self.stock, self.built, self.mods)

        expected = {**ours, ('gui', 2): b'HD', ('extra', 5): b'added', ('music', 3): b'new audio'}
        del expected['obsolete', 4]
        self.assertEqual(contents(paths[1].read_bytes()), expected)
        self.assertFalse((self.built / 'unrelated.bin').exists())
        self.assertEqual({p: p.read_bytes() for p in snapshots}, snapshots)

    def test_conflicting_changes_and_delete_edit_are_atomic(self):
        k = ('button', 1)
        (self.stock / 'a.bin').write_bytes(b'base')
        (self.built / 'a.bin').write_bytes(b'base')
        (self.mods[0] / 'romfs/a.bin').write_bytes(b'change pending')
        (self.stock / 'z.arc').write_bytes(archive({k: b'base'}))
        (self.built / 'z.arc').write_bytes(archive({k: b'xbox'}))
        for mod_members in [{k: b'custom'}, {}]:
            with self.subTest(mod_members=mod_members):
                (self.mods[0] / 'romfs/z.arc').write_bytes(archive(mod_members))
                with self.assertRaisesRegex(ValueError, 'conflicting changes.*button'):
                    merge_mods(self.stock, self.built, self.mods)
                self.assertEqual((self.built / 'a.bin').read_bytes(), b'base')
                self.assertEqual(contents((self.built / 'z.arc').read_bytes()), {k: b'xbox'})

    def test_loose_file_conflicts_across_mods(self):
        for root in [self.stock, self.built]:
            (root / 'shared.bin').write_bytes(b'base')
        for i, mod in enumerate(self.mods):
            (mod / 'romfs/shared.bin').write_bytes(bytes([i]))
        with self.assertRaisesRegex(ValueError, 'conflicting changes.*shared.bin'):
            merge_mods(self.stock, self.built, self.mods)
        self.assertEqual((self.built / 'shared.bin').read_bytes(), b'base')
        (self.mods[1] / 'romfs/shared.bin').write_bytes(b'\0')
        merge_mods(self.stock, self.built, self.mods)
        self.assertEqual((self.built / 'shared.bin').read_bytes(), b'\0')

    def test_refuses_escaping_symlinks(self):
        for root in [self.stock, self.built]:
            (root / 'shared.bin').write_bytes(b'base')
        (self.mods[0] / 'romfs/shared.bin').symlink_to(self.stock / 'shared.bin')
        with self.assertRaises(ValueError):
            merge_mods(self.stock, self.built, self.mods)
        self.assertEqual((self.built / 'shared.bin').read_bytes(), b'base')


if __name__ == '__main__':
    unittest.main()
