import unittest

from djlib_doctor.cues import CueKind, CueType, parse_cue_num, parse_cue_type


class CuePolicyTests(unittest.TestCase):
    def test_rekordbox_num_minus_one_is_memory_cue(self):
        kind, slot = parse_cue_num("-1")

        self.assertIs(kind, CueKind.MEMORY)
        self.assertIsNone(slot)

    def test_rekordbox_num_zero_is_hotcue_a(self):
        kind, slot = parse_cue_num("0")

        self.assertIs(kind, CueKind.HOTCUE)
        self.assertEqual(slot, 0)

    def test_rekordbox_type_four_is_loop(self):
        self.assertIs(parse_cue_type("4"), CueType.LOOP)


if __name__ == "__main__":
    unittest.main()
