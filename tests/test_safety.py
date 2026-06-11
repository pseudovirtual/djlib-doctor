from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from djlib_doctor.safety import all_checks_passed, check_rekordbox_db_sidecars, check_serato_sqlite_sidecars, timestamped_backup_path


class SafetyTests(unittest.TestCase):
    def test_db_sidecar_checks_fail_when_wal_exists(self):
        with TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "master.db"
            db.write_bytes(b"db")
            db.with_name("master.db-wal").write_bytes(b"wal")

            checks = check_rekordbox_db_sidecars(db)

            self.assertFalse(all_checks_passed(checks))
            self.assertFalse(checks[0].passed)
            self.assertTrue(checks[1].passed)
            self.assertTrue(checks[2].passed)

    def test_serato_sqlite_sidecar_checks_include_journal(self):
        with TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "root.sqlite"
            db.write_bytes(b"db")
            db.with_name("root.sqlite-journal").write_bytes(b"journal")

            checks = check_serato_sqlite_sidecars(db)

            self.assertFalse(all_checks_passed(checks))
            self.assertEqual(checks[0].code, "serato_sqlite_sidecar_absent")
            self.assertFalse(checks[2].passed)

    def test_timestamped_backup_path_is_predictable(self):
        backup = timestamped_backup_path(Path("/tmp/master.db"), "before-test", datetime(2026, 6, 5, 12, 30, 45))

        self.assertEqual(str(backup), "/tmp/master.before-test.20260605-123045.db")


if __name__ == "__main__":
    unittest.main()
