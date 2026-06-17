from pathlib import Path
import json
import unittest

from djlib_doctor.serato_markers import parse_markers2_payload


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "serato_golden"


class SeratoGoldenFixtureTests(unittest.TestCase):
    def test_markers2_vectors_are_vendored_with_provenance(self):
        paths = sorted(FIXTURE_DIR.glob("markers2-*.json"))
        self.assertGreaterEqual(len(paths), 2)
        for path in paths:
            fixture = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("provenance", fixture)
            self.assertIn("Holzhaus/serato-tags", fixture["provenance"])
            self.assertEqual(parse_markers2_payload(bytes.fromhex(fixture["payload_hex"])), tuple(fixture["expected_markers"]))


if __name__ == "__main__":
    unittest.main()
