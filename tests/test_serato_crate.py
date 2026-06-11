from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from djlib_doctor.serato_crate import CRATE_VERSION, read_serato_crate, safe_crate_filename, write_serato_crate


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


if __name__ == "__main__":
    unittest.main()
