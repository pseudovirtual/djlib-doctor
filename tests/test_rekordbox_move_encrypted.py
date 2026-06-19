import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests.support.fake_pyrekordbox_db import FakePyrekordboxDb
from tests.support.rekordbox_encrypted_assertions import read_encrypted_master_copy, rekordbox_not_running
from tests.support.rekordbox_encrypted_fixture import (
    SqlcipherUnavailable,
    generate_encrypted_rekordbox_fixture,
    skip_or_fail_for_missing_encrypted_backend,
)

from djlib_doctor.rekordbox_move import stage_rekordbox_move


class RekordboxMoveEncryptedTests(unittest.TestCase):
    def test_move_stages_encrypted_master_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            try:
                fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            except (ImportError, SqlcipherUnavailable) as exc:
                skip_or_fail_for_missing_encrypted_backend(self, exc)
            source = tmp / "Old Folder" / "Track One.aiff"
            target = tmp / "New Folder" / "Track One Renamed.aiff"
            source.parent.mkdir()
            source.write_bytes(b"audio")
            operations = _write_operations(tmp, source, target)

            with rekordbox_not_running():
                stage = stage_rekordbox_move(fixture.encrypted_db, operations, tmp / "stage")
                library = read_encrypted_master_copy(stage.staged_db, tmp / "copied-move-master.db")

        self.assertEqual(library.tracks[0].path, target)

    def test_move_uses_encrypted_opener_when_plain_sqlite_rejects_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            source = tmp / "Old Folder" / "Track One.aiff"
            target = tmp / "New Folder" / "Track One Renamed.aiff"
            fake_db = FakePyrekordboxDb()
            db.write_bytes(b"not a plain sqlite database")
            source.parent.mkdir()
            source.write_bytes(b"audio")
            operations = _write_operations(tmp, source, target)

            with patch("djlib_doctor.rekordbox_pyrekordbox.open_master_database", return_value=fake_db):
                stage = stage_rekordbox_move(db, operations, tmp / "stage")
            stage_exists = stage.stage_manifest_path.exists()

        self.assertTrue(stage_exists)
        self.assertTrue(fake_db.closed)
        self.assertTrue(fake_db.disposed)
        self.assertTrue(any("UPDATE" in statement and "djmdContent" in statement for statement in fake_db.statements))
        self.assertIn("PRAGMA wal_checkpoint(TRUNCATE)", fake_db.statements)


def _write_operations(tmp: Path, source: Path, target: Path) -> Path:
    operations = tmp / "move.json"
    operations.write_text(
        json.dumps({"operations": [{"track_id": "1", "source": str(source), "target": str(target)}]}),
        encoding="utf-8",
    )
    return operations


if __name__ == "__main__":
    unittest.main()
