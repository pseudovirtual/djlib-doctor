from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import sqlite3
import unittest

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, write_config
from djlib_doctor.serato_crate import read_serato_crate
from tests.helpers import insert_serato_asset, make_rekordbox_import_db, make_serato_root


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class SyncRunnerTests(unittest.TestCase):
    def test_sync_cli_installs_rekordbox_primary_to_serato_with_apply_and_yes(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library, music, config_path = _rekordbox_config(tmp)

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(_sync_args(config_path, tmp / "sync", apply=True))
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
                exit_code = main(_sync_args(config_path, tmp / "sync", apply=True, yes=False))
            self.assertFalse((tmp / "sync" / "serato-stage").exists())

        self.assertEqual(exit_code, 3)
        self.assertIn("--yes", stderr.getvalue())

    def test_sync_cli_is_dry_run_without_apply_even_with_yes(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config_path = tmp / "config.json"
            write_config(config_path, default_config(primary="rekordbox", rekordbox_xml=FIXTURE))

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(_sync_args(config_path, tmp / "sync"))
            manifest_exists = (tmp / "sync" / "port" / "port-manifest.json").exists()
            stage_exists = (tmp / "sync" / "serato-stage").exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(manifest_exists)
        self.assertFalse(stage_exists)

    def test_sync_cli_installs_serato_primary_to_rekordbox_with_apply_and_yes(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db, config_path = _serato_config(tmp)

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = main(_sync_args(config_path, tmp / "sync", apply=True))
            conn = sqlite3.connect(db)
            try:
                title = conn.execute("SELECT Title FROM djmdContent").fetchone()[0]
            finally:
                conn.close()

        self.assertEqual(exit_code, 0)
        self.assertEqual(title, "Track One")


def _rekordbox_config(tmp: Path) -> tuple[Path, Path, Path]:
    library = tmp / "Library"
    music = tmp / "_Serato_"
    library.mkdir()
    music.mkdir()
    make_serato_root(library / "root.sqlite")
    config_path = tmp / "config.json"
    write_config(
        config_path,
        default_config(primary="rekordbox", rekordbox_xml=FIXTURE, serato_library_dir=library, serato_music_dir=music),
    )
    return library, music, config_path


def _serato_config(tmp: Path) -> tuple[Path, Path]:
    library = tmp / "Library"
    library.mkdir()
    make_serato_root(library / "root.sqlite")
    insert_serato_asset(library / "root.sqlite", "Music/Track One.aiff")
    db = tmp / "master.db"
    make_rekordbox_import_db(db)
    config_path = tmp / "config.json"
    write_config(config_path, default_config(primary="serato", serato_library_dir=library, music_root=tmp, rekordbox_db=db))
    return db, config_path


def _sync_args(config: Path, out: Path, apply: bool = False, yes: bool = True) -> list[str]:
    args = ["sync", "--config", str(config), "--collection", "--out", str(out)]
    if apply:
        args.append("--apply")
    if yes:
        args.append("--yes")
    return args + ["--skip-process-check"]


if __name__ == "__main__":
    unittest.main()
