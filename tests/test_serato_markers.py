import unittest

from djlib_doctor.serato_markers import parse_markers2_payload


class SeratoMarkersGoldenVectorTests(unittest.TestCase):
    def test_parse_reference_hotcue_vector(self):
        payload = bytes.fromhex(
            "01 01"
            " 43 55 45 00 00 00 00 12"
            " 00 02 00 00 56 ce 00 cc cc 00 00 00"
            " 43 75 65 20 43 00"
        )

        self.assertEqual(
            parse_markers2_payload(payload),
            (
                {
                    "kind": "hotcue",
                    "cue_type": "cue",
                    "start_ms": 22222,
                    "end_ms": None,
                    "slot": 2,
                    "label": "Cue C",
                    "color": "cccc00",
                },
            ),
        )

    def test_parse_reference_saved_loop_vector(self):
        payload = bytes.fromhex(
            "01 01"
            " 4c 4f 4f 50 00 00 00 00 1b"
            " 00 03 00 00 fa 00 00 01 38 80"
            " 00 00 00 00 00 00 00 ff cc 00"
            " 4c 6f 6f 70 20 44 00"
        )

        self.assertEqual(
            parse_markers2_payload(payload),
            (
                {
                    "kind": "loop",
                    "cue_type": "loop",
                    "start_ms": 64000,
                    "end_ms": 80000,
                    "slot": 3,
                    "label": "Loop D",
                    "color": "cc",
                },
            ),
        )


if __name__ == "__main__":
    unittest.main()
