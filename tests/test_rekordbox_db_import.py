import contextlib
import io
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.io_utils import write_json
from djlib_doctor.rekordbox_db_stage import stage_rekordbox_db_import
from djlib_doctor.serato_crate import write_serato_crate


def make_port_manifest(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": "1.0",
            "mode": "dry_run_only",
            "source_platform": "serato",
            "target_platform": "rekordbox_xml",
            "transfer_mode": "full",
            "tracks": [
                {
                    "track_id": "1",
                    "portable_id": "Music/Track One.aiff",
                    "path": "/Music/Track One.aiff",
                    "title": "Track One",
                    "artist": "Artist One",
                    "album": "Album",
                    "genre": "House",
                    "key": "8A",
                    "bpm": 124.0,
                    "length_ms": 300000,
                    "cues": [
                        {
                            "kind": "hotcue",
                            "cue_type": "cue",
                            "start_ms": 12345,
                            "end_ms": None,
                            "slot": 0,
                            "label": "Cue A",
                        },
                        {
                            "kind": "hotcue",
                            "cue_type": "loop",
                            "start_ms": 48000,
                            "end_ms": 56000,
                            "slot": 1,
                            "label": "Loop B",
                        },
                    ],
                }
            ],
            "skipped": [],
        },
    )


def make_rekordbox_db(path: Path, supported: bool = True) -> None:
    conn = sqlite3.connect(path)
    try:
        if supported:
            conn.execute(
                """
                CREATE TABLE djmdContent(
                    ID INTEGER PRIMARY KEY,
                    FolderPath TEXT,
                    FileNameL TEXT,
                    Title TEXT,
                    ArtistName TEXT,
                    AlbumName TEXT,
                    GenreName TEXT,
                    KeyName TEXT,
                    BPM REAL,
                    Length INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE djmdCue(
                    ID INTEGER PRIMARY KEY,
                    ContentID INTEGER,
                    InMsec INTEGER,
                    OutMsec INTEGER,
                    Kind INTEGER,
                    HotCue INTEGER,
                    Name TEXT
                )
                """
            )
        else:
            conn.execute("CREATE TABLE something_else(id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()


class RekordboxDbImportTests(unittest.TestCase):
    def test_stage_rekordbox_db_import_from_serato_port_manifest(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            make_rekordbox_db(db)
            make_port_manifest(manifest)

            stage = stage_rekordbox_db_import(db, manifest, tmp / "stage")
            ops = json.loads((tmp / "stage" / "rekordbox-db-import-operations.json").read_text(encoding="utf-8"))
            conn = sqlite3.connect(stage.staged_db)
            try:
                row = conn.execute("SELECT Title, ArtistName, BPM FROM djmdContent").fetchone()
                cue_rows = conn.execute(
                    "SELECT ContentID, InMsec, OutMsec, Kind, HotCue, Name FROM djmdCue ORDER BY ID"
                ).fetchall()
            finally:
                conn.close()

        self.assertEqual(ops["summary"], {"insert": 3, "update": 0})
        self.assertEqual(row, ("Track One", "Artist One", 124.0))
        self.assertEqual(cue_rows, [(1, 12345, None, 0, 0, "Cue A"), (1, 48000, 56000, 4, 1, "Loop B")])

    def test_cli_stage_rekordbox_db_import_prints_install_token(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            make_rekordbox_db(db)
            make_port_manifest(manifest)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "stage",
                        "rekordbox-db-import",
                        "--db",
                        str(db),
                        "--port-manifest",
                        str(manifest),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox DB import stage written:", stdout.getvalue())
        self.assertIn("Install token: INSTALL_SQLITE_STAGE:", stdout.getvalue())

    def test_cli_migrate_serato_to_rb_can_stage_rekordbox_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            db = tmp / "master.db"
            crate = tmp / "Test.crate"
            make_rekordbox_db(db)
            _make_serato_root(library / "root.sqlite")
            write_serato_crate(crate, ("Music/Track One.aiff",))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "migrate",
                        "serato-to-rb",
                        "--serato-library-dir",
                        str(library),
                        "--crate",
                        str(crate),
                        "--collection-root",
                        "/Music",
                        "--out",
                        str(tmp / "out"),
                        "--stage-db",
                        "--rekordbox-db",
                        str(db),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Rekordbox DB stage:", stdout.getvalue())
            self.assertTrue((tmp / "out" / "rekordbox-stage" / "rekordbox-db-stage-manifest.json").exists())

    def test_rekordbox_db_import_refuses_unsupported_schema(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            make_rekordbox_db(db, supported=False)
            make_port_manifest(manifest)

            with self.assertRaises(ValueError):
                stage_rekordbox_db_import(db, manifest, tmp / "stage")

    def test_rekordbox_db_import_refuses_encrypted_sqlcipher_db_clearly(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            db.write_bytes(b"SQLCipher encrypted Rekordbox database placeholder")
            make_port_manifest(manifest)

            with self.assertRaisesRegex(ValueError, r"encrypted SQLCipher.*pyrekordbox-backed importer"):
                stage_rekordbox_db_import(db, manifest, tmp / "stage")


def _make_serato_root(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE asset(portable_id TEXT, name TEXT, artist TEXT)")
        conn.execute("INSERT INTO asset VALUES('Music/Track One.aiff', 'Track One', 'Artist One')")
        conn.commit()
    finally:
        conn.close()
