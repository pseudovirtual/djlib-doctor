import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from djlib_doctor.stage_common import install_token
from djlib_doctor.stage_installer import (
    backup_and_replace,
    copy_required_backup,
    require_app_closed,
    require_file_hash,
    require_no_sqlite_sidecars,
    require_stage_token,
    restore_backups,
)


class StageInstallerTests(unittest.TestCase):
    def test_require_stage_token_recomputes_payload(self):
        payload = {"hashes": {"staged": "abc"}}
        token = install_token("INSTALL_TEST", payload)

        require_stage_token("INSTALL_TEST", payload, token, token)

        with self.assertRaises(RuntimeError):
            require_stage_token("INSTALL_TEST", {"hashes": {"staged": "tampered"}}, token, token)

    def test_require_no_sqlite_sidecars_fails_closed(self):
        with TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "master.db"
            db.write_bytes(b"db")
            db.with_name("master.db-wal").write_bytes(b"live wal")

            with self.assertRaises(RuntimeError):
                require_no_sqlite_sidecars(db, "rekordbox_sqlite_sidecar_absent", "sidecars exist")

    def test_require_file_hash_fails_closed_for_stale_source(self):
        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "track.aiff"
            source.write_bytes(b"before")
            expected_hash = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

            with self.assertRaises(RuntimeError):
                require_file_hash(source, expected_hash, "Live source")

    def test_require_app_closed_fails_closed_when_app_is_running(self):
        with self.assertRaises(RuntimeError):
            require_app_closed(("123 /Applications/rekordbox.app/rekordbox",), {"rekordbox": ("rekordbox",)}, "running")

    def test_copy_required_backup_verifies_backup_exists(self):
        with TemporaryDirectory() as tmpdir:
            source = Path(tmpdir) / "source.db"
            backup = Path(tmpdir) / "backups" / "source.db"
            source.write_bytes(b"db")

            copy_required_backup(source, backup)

            self.assertEqual(backup.read_bytes(), b"db")

    def test_backup_and_replace_failure_leaves_original_and_backup(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            staged = root / "staged.db"
            live = root / "master.db"
            backup = root / "backups" / "master.db"
            staged.write_bytes(b"new")
            live.write_bytes(b"original")

            with mock.patch("djlib_doctor.stage_installer.os.replace", side_effect=OSError("replace failed")):
                with self.assertRaises(OSError):
                    backup_and_replace(staged, live, backup)

            self.assertEqual(live.read_bytes(), b"original")
            self.assertEqual(backup.read_bytes(), b"original")

    def test_restore_backups_restores_existing_and_removes_created_paths(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            existing = root / "existing.txt"
            created = root / "created.txt"
            backup = root / "backup.txt"
            existing.write_text("changed", encoding="utf-8")
            created.write_text("new", encoding="utf-8")
            backup.write_text("original", encoding="utf-8")

            restore_backups(
                [
                    {"path": str(existing), "backup": str(backup), "existed": True},
                    {"path": str(created), "backup": "", "existed": False},
                ]
            )

            self.assertEqual(existing.read_text(encoding="utf-8"), "original")
            self.assertFalse(created.exists())


if __name__ == "__main__":
    unittest.main()
