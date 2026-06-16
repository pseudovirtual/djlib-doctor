from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import sqlite3
import unittest

from djlib_doctor.cli import main
from djlib_doctor.port_serato_rekordbox import build_serato_to_rekordbox_plan, write_serato_to_rekordbox_plan
from djlib_doctor.serato_crate import write_serato_crate


def make_serato_root(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE asset(
                id INTEGER PRIMARY KEY,
                portable_id TEXT,
                name TEXT,
                artist TEXT,
                album TEXT,
                genre TEXT,
                key TEXT,
                bpm REAL,
                length_ms INTEGER
            );
            INSERT INTO asset(id, portable_id, name, artist, album, genre, key, bpm, length_ms)
            VALUES(1, 'Music/Track One.aiff', 'Track One', 'Artist One', 'Album', 'House', '8A', 124.0, 300000);
            INSERT INTO asset(id, portable_id, name, artist)
            VALUES(2, 'soundcloud:tracks:123', 'Stream', 'Artist Two');
            """
        )
        conn.commit()
    finally:
        conn.close()


class PortRekordboxTests(unittest.TestCase):
    def test_build_serato_to_rekordbox_plan_maps_crate_tracks(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            crate = tmp / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff", "soundcloud:tracks:123"))

            plan = build_serato_to_rekordbox_plan(library, crate, collection_root=Path("/Users/test"))

        self.assertEqual(plan.summary["tracks"], 1)
        self.assertEqual(plan.summary["skipped"], 1)
        self.assertEqual(plan.tracks[0].path, "/Users/test/Music/Track One.aiff")
        self.assertEqual(plan.skipped[0]["reason"], "not_local_file")

    def test_write_serato_to_rekordbox_plan_writes_manifest_and_xml_preview(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            crate = tmp / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff",))

            plan = build_serato_to_rekordbox_plan(library, crate, collection_root=Path("/Users/test"))
            outputs = write_serato_to_rekordbox_plan(plan, tmp / "out")
            manifest = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
            xml = Path(outputs["rekordbox_xml_preview"]).read_text(encoding="utf-8")

        self.assertEqual(manifest["target_platform"], "rekordbox_xml")
        self.assertIn("<DJ_PLAYLISTS", xml)
        self.assertIn("Track One", xml)

    def test_port_cli_serato_to_rb_writes_outputs(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            crate = tmp / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff",))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "port",
                        "serato-to-rb",
                        "--serato-library-dir",
                        str(library),
                        "--crate",
                        str(crate),
                        "--collection-root",
                        "/Users/test",
                        "--out",
                        str(tmp / "out"),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox XML preview written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
