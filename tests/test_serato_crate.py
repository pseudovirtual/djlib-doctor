import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.serato_crate import CRATE_VERSION, read_serato_crate, safe_crate_filename, write_serato_crate

GOLDEN = Path(__file__).parent / "fixtures" / "serato_golden" / "crate-simple.json"


class SeratoCrateTests(unittest.TestCase):
    def test_serato_crate_round_trips_portable_ids(self):
        with TemporaryDirectory() as tmpdir:
            crate_path = Path(tmpdir) / "Fixture.crate"
            portable_ids = ("Music/Track One.aiff", "Music/Track Two.wav")

            write_serato_crate(crate_path, portable_ids)
            crate = read_serato_crate(crate_path)

        self.assertEqual(crate.version, CRATE_VERSION)
        self.assertEqual(crate.tracks, portable_ids)

    def test_safe_crate_filename_removes_path_separators(self):
        self.assertEqual(safe_crate_filename("RB / Test: Crate"), "RB - Test - Crate")

    def test_serato_crate_matches_golden_vector(self):
        fixture = json.loads(GOLDEN.read_text(encoding="utf-8"))
        expected = bytes.fromhex(fixture["payload_hex"])
        with TemporaryDirectory() as tmpdir:
            crate_path = Path(tmpdir) / "Golden.crate"
            crate_path.write_bytes(expected)

            crate = read_serato_crate(crate_path)
            written = Path(tmpdir) / "Written.crate"
            write_serato_crate(written, tuple(fixture["tracks"]))
            written_bytes = written.read_bytes()

        self.assertIn("Serato crate TLV", fixture["provenance"])
        self.assertEqual(crate.version, CRATE_VERSION)
        self.assertEqual(crate.tracks, tuple(fixture["tracks"]))
        self.assertEqual(written_bytes, expected)


if __name__ == "__main__":
    unittest.main()
