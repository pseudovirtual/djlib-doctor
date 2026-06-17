import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.serato_database_v2 import read_serato_database_v2
from djlib_doctor.serato_tlv import record, text


class SeratoDatabaseV2Tests(unittest.TestCase):
    def test_database_v2_reads_tracks_from_tlv_records(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "database V2"
            path.write_bytes(
                b"".join(
                    (
                        record("vrsn", text("1.0/Serato ScratchLive Database")),
                        record("otrk", record("ptrk", text("Music/Track One.aiff"))),
                        record("otrk", record("ptrk", text("Music/Track Two.mp3"))),
                    )
                )
            )

            database = read_serato_database_v2(path)

        self.assertEqual(database.version, "1.0/Serato ScratchLive Database")
        self.assertEqual(database.tracks, ("Music/Track One.aiff", "Music/Track Two.mp3"))


if __name__ == "__main__":
    unittest.main()
