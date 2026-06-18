import contextlib
import io
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main


class RekordboxMoveTests(unittest.TestCase):
    def test_stage_and_install_moves_file_and_updates_db_path(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Old Folder" / "Track One.aiff"
            target = tmp / "New Folder" / "Track One Renamed.aiff"
            db = tmp / "master.db"
            source.parent.mkdir()
            source.write_bytes(b"audio")
            _make_rekordbox_db(db, source)
            operations = _write_operations(tmp, source, target)

            with contextlib.redirect_stdout(io.StringIO()):
                stage_exit = main(
                    [
                        "stage",
                        "rekordbox-move",
                        "--db",
                        str(db),
                        "--operations",
                        str(operations),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )
            manifest = json.loads((tmp / "stage" / "rekordbox-move-stage-manifest.json").read_text())
            staged_row = _content_row(tmp / "stage" / "master.db")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                install_exit = main(
                    [
                        "install",
                        "rekordbox-move",
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--db",
                        str(db),
                        "--confirm-token",
                        manifest["install_token"],
                        "--skip-process-check",
                    ]
                )
            source_exists = source.exists()
            target_bytes = target.read_bytes()
            installed_row = _content_row(db)
            report_exists = (tmp / "stage" / "rekordbox-move-install-report.json").is_file()

        self.assertEqual(stage_exit, 0)
        self.assertEqual(install_exit, 0)
        self.assertEqual(staged_row, (str(target.parent), target.name))
        self.assertFalse(source_exists)
        self.assertEqual(target_bytes, b"audio")
        self.assertEqual(installed_row, (str(target.parent), target.name))
        self.assertTrue(report_exists)

    def test_install_refuses_when_source_hash_changed_after_staging(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Old Folder" / "Track One.aiff"
            target = tmp / "New Folder" / "Track One Renamed.aiff"
            db = tmp / "master.db"
            source.parent.mkdir()
            source.write_bytes(b"audio")
            _make_rekordbox_db(db, source)
            operations = _write_operations(tmp, source, target)

            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "stage",
                            "rekordbox-move",
                            "--db",
                            str(db),
                            "--operations",
                            str(operations),
                            "--stage-dir",
                            str(tmp / "stage"),
                        ]
                    ),
                    0,
                )
            source.write_bytes(b"changed")
            manifest = json.loads((tmp / "stage" / "rekordbox-move-stage-manifest.json").read_text())
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                install_exit = main(
                    [
                        "install",
                        "rekordbox-move",
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--db",
                        str(db),
                        "--confirm-token",
                        manifest["install_token"],
                        "--skip-process-check",
                    ]
                )
            source_exists = source.exists()
            target_exists = target.exists()
            installed_row = _content_row(db)

        self.assertEqual(install_exit, 3)
        self.assertTrue(source_exists)
        self.assertFalse(target_exists)
        self.assertEqual(installed_row, (str(source.parent), source.name))


def _make_rekordbox_db(path: Path, audio: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript("CREATE TABLE djmdContent(ID INTEGER PRIMARY KEY, FolderPath TEXT, FileNameL TEXT);")
        conn.execute(
            "INSERT INTO djmdContent(ID, FolderPath, FileNameL) VALUES(1, ?, ?)",
            (str(audio.parent), audio.name),
        )
        conn.commit()
    finally:
        conn.close()


def _content_row(path: Path) -> tuple[str, str]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT FolderPath, FileNameL FROM djmdContent WHERE ID = 1").fetchone()
    finally:
        conn.close()


def _write_operations(tmp: Path, source: Path, target: Path) -> Path:
    operations = tmp / "move.json"
    operations.write_text(
        json.dumps({"operations": [{"track_id": "1", "source": str(source), "target": str(target)}]}),
        encoding="utf-8",
    )
    return operations
