from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import sqlite3
import unittest

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, write_config
from djlib_doctor.serato_crate import read_serato_crate
from djlib_doctor.sync_planner import plan_sync
from tests.helpers import make_serato_root


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class SyncPlannerTests(unittest.TestCase):
    def test_plans_rekordbox_primary_to_serato(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config = default_config(primary="rekordbox", rekordbox_xml=FIXTURE)

            result = plan_sync(config, tmp / "sync", collection=True)
            manifest = json.loads(result.port_manifest.read_text(encoding="utf-8"))

        self.assertEqual(result.direction, "rb-to-serato")
        self.assertEqual(manifest["source_platform"], "rekordbox_xml")
        self.assertEqual(manifest["target_platform"], "serato")
        self.assertTrue(result.certification.passed)

    def test_plans_serato_primary_to_rekordbox(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            _insert_serato_asset(library / "root.sqlite", "Music/Track One.aiff")
            config = default_config(primary="serato", serato_library_dir=library, music_root=tmp)

            result = plan_sync(config, tmp / "sync", collection=True)
            manifest = json.loads(result.port_manifest.read_text(encoding="utf-8"))

        self.assertEqual(result.direction, "serato-to-rb")
        self.assertEqual(manifest["source_platform"], "serato")
        self.assertEqual(manifest["target_platform"], "rekordbox_xml")
        self.assertTrue(result.certification.passed)

    def test_sync_plan_cli_uses_primary_direction(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config_path = tmp / "config.json"
            write_config(config_path, default_config(primary="rekordbox", rekordbox_xml=FIXTURE))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["sync", "plan", "--config", str(config_path), "--collection", "--out", str(tmp / "sync")])

            manifest = json.loads((tmp / "sync" / "port" / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("Direction: rb-to-serato", stdout.getvalue())
        self.assertEqual(manifest["target_platform"], "serato")

    def test_sync_cli_installs_rekordbox_primary_to_serato_with_yes(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            music = tmp / "_Serato_"
            library.mkdir()
            music.mkdir()
            make_serato_root(library / "root.sqlite")
            config_path = tmp / "config.json"
            write_config(
                config_path,
                default_config(
                    primary="rekordbox",
                    rekordbox_xml=FIXTURE,
                    serato_library_dir=library,
                    serato_music_dir=music,
                ),
            )

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "sync",
                        "--config",
                        str(config_path),
                        "--collection",
                        "--out",
                        str(tmp / "sync"),
                        "--yes",
                        "--skip-process-check",
                    ]
                )
            crates = tuple((music / "Subcrates").glob("*.crate"))
            crate_track_count = len(read_serato_crate(crates[0]).tracks) if crates else 0

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(crates), 1)
        self.assertGreater(crate_track_count, 0)

    def test_sync_cli_requires_noninteractive_approval_before_staging(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config_path = tmp / "config.json"
            write_config(config_path, default_config(primary="rekordbox", rekordbox_xml=FIXTURE))
            stderr = io.StringIO()

            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
                exit_code = main(["sync", "--config", str(config_path), "--collection", "--out", str(tmp / "sync")])

            self.assertFalse((tmp / "sync" / "serato-stage").exists())

        self.assertEqual(exit_code, 3)
        self.assertIn("--yes", stderr.getvalue())

    def test_sync_cli_installs_serato_primary_to_rekordbox_with_yes(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            _insert_serato_asset(library / "root.sqlite", "Music/Track One.aiff")
            db = tmp / "master.db"
            _make_rekordbox_db(db)
            config_path = tmp / "config.json"
            write_config(
                config_path,
                default_config(primary="serato", serato_library_dir=library, music_root=tmp, rekordbox_db=db),
            )

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(
                    [
                        "sync",
                        "--config",
                        str(config_path),
                        "--collection",
                        "--out",
                        str(tmp / "sync"),
                        "--yes",
                        "--skip-process-check",
                    ]
                )
            conn = sqlite3.connect(db)
            try:
                title = conn.execute("SELECT Title FROM djmdContent").fetchone()[0]
            finally:
                conn.close()

        self.assertEqual(exit_code, 0)
        self.assertEqual(title, "Track One")


def _insert_serato_asset(root_sqlite: Path, portable_id: str) -> None:
    conn = sqlite3.connect(root_sqlite)
    try:
        conn.execute(
            "INSERT INTO asset(revision, portable_id, file_name, name, artist) VALUES(?, ?, ?, ?, ?)",
            (1, portable_id, Path(portable_id).name, Path(portable_id).stem, "Artist One"),
        )
        conn.commit()
    finally:
        conn.close()


def _make_rekordbox_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE djmdContent(
                ID INTEGER PRIMARY KEY,
                FolderPath TEXT,
                FileNameL TEXT,
                Title TEXT,
                ArtistName TEXT
            );
            CREATE TABLE djmdCue(
                ID INTEGER PRIMARY KEY,
                ContentID INTEGER,
                InMsec INTEGER,
                OutMsec INTEGER,
                Kind INTEGER,
                HotCue INTEGER,
                Name TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    unittest.main()
