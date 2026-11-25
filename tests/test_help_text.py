import struct
import unittest

from build_help import update_gmd


def gmd(text):
    body = text.encode('utf-8')
    header = bytearray(40)
    header[:8] = bytes.fromhex('474d440002030100')
    struct.pack_into('<I', header, 32, len(body))
    return bytes(header) + body


class HelpTextTests(unittest.TestCase):
    def test_hunter_arts_in_menu_and_notes(self):
        cases = [
            ('ZL键与X、A、B键分别同按发动狩技，', 'LT键与Y、B、A键分别同按发动狩技，'),
            ('同时按下ZL键和X或A或B键，', '同时按下LT键和Y或B或A键，'),
            ('同时按下X和A键', '同时按下Y和B键'),
            ('L/R键的动作', 'LB/RB键的动作'),
        ]
        for original, expected in cases:
            with self.subTest(original=original):
                self.assertEqual(update_gmd(gmd(original)), gmd(expected))

    def test_preserves_entry_boundaries_and_non_button_text(self):
        unrelated = '按照A、B、C的顺序降低。<ICON PAD_R>\0LB键\0'
        original = unrelated + 'R+A+B键\0ZL＋ZR按钮\0'
        expected = unrelated + 'RB+B+A键\0LT＋RT按钮\0'
        self.assertEqual(update_gmd(gmd(original)), gmd(expected))


if __name__ == '__main__':
    unittest.main()
