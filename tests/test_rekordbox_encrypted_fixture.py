import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support.rekordbox_encrypted_fixture import (
    SqlcipherUnavailable,
    build_plain_rekordbox_fixture_db,
    generate_encrypted_rekordbox_fixture,
    skip_or_fail_for_missing_encrypted_backend,
)


class RekordboxEncryptedFixtureTests(unittest.TestCase):
    def test_plain_fixture_schema_matches_target_tables(self):
        with TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "plain-master.db"

            build_plain_rekordbox_fixture_db(db)
            conn = sqlite3.connect(db)
            try:
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                content = conn.execute("SELECT FolderPath, FileNameL, Title FROM djmdContent").fetchone()
                cue_columns = {row[1] for row in conn.execute("PRAGMA table_info(djmdCue)")}
                cue = conn.execute(
                    "SELECT InMsec, OutMsec, Kind, is_hot_cue, is_memory_cue, Comment FROM djmdCue"
                ).fetchone()
            finally:
                conn.close()

        self.assertIn("djmdContent", tables)
        self.assertIn("djmdCue", tables)
        self.assertNotIn("HotCue", cue_columns)
        self.assertEqual(content, ("/Music", "Track One.aiff", "Track One"))
        self.assertEqual(cue, (12345, -1, 1, 1, 0, "Cue A"))

    def test_generate_encrypted_fixture_or_skip_when_sqlcipher_missing(self):
        with TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "encrypted-master.db"
            try:
                result = generate_encrypted_rekordbox_fixture(out)
            except SqlcipherUnavailable as exc:
                skip_or_fail_for_missing_encrypted_backend(self, exc)

            self.assertTrue(result.encrypted_db.exists())
            self.assertTrue(result.plain_db.exists())
            self.assertEqual(result.schema, "sqlcipher4")


if __name__ == "__main__":
    unittest.main()
