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
                        record("otrk", record("pfil", text("Music/Track One.aiff"))),
                        record("otrk", record("pfil", text("Music/Track Two.mp3"))),
                    )
                )
            )

            database = read_serato_database_v2(path)

        self.assertEqual(database.version, "1.0/Serato ScratchLive Database")
        self.assertEqual(database.track_paths, ("Music/Track One.aiff", "Music/Track Two.mp3"))

    def test_database_v2_reads_real_nested_otrk_records_with_metadata(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "database V2"
            path.write_bytes(
                b"".join(
                    (
                        record("vrsn", text("1.0/Serato ScratchLive Database")),
                        record(
                            "otrk",
                            record(
                                "info",
                                b"".join(
                                    (
                                        record("pfil", text("Music/Nested Track.aiff")),
                                        record("tsng", text("Nested Track")),
                                        record("tart", text("Fixture Artist")),
                                        record("talb", text("Fixture Album")),
                                        record("tgen", text("House")),
                                        record("tkey", text("8A")),
                                        record("tbpm", text("124.50")),
                                    )
                                ),
                            ),
                        ),
                    )
                )
            )

            database = read_serato_database_v2(path)

        self.assertEqual(database.track_paths, ("Music/Nested Track.aiff",))
        self.assertEqual(database.tracks[0].title, "Nested Track")
        self.assertEqual(database.tracks[0].artist, "Fixture Artist")
        self.assertEqual(database.tracks[0].album, "Fixture Album")
        self.assertEqual(database.tracks[0].genre, "House")
        self.assertEqual(database.tracks[0].key, "8A")
        self.assertEqual(database.tracks[0].bpm, 124.5)

    def test_database_v2_does_not_treat_crate_ptrk_as_track_path(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "database V2"
            path.write_bytes(record("otrk", record("ptrk", text("Music/Wrong Field.aiff"))))

            database = read_serato_database_v2(path)

        self.assertEqual(database.track_paths, ())


if __name__ == "__main__":
    unittest.main()
