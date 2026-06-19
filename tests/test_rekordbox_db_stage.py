import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support.rekordbox_encrypted_assertions import (
    assert_plain_sqlite_rejects,
    read_encrypted_library,
    read_encrypted_master_copy,
    rekordbox_not_running,
)
from tests.support.rekordbox_encrypted_fixture import (
    generate_encrypted_rekordbox_fixture,
    requires_rekordbox_backend,
)

from djlib_doctor.rekordbox_db_stage import install_rekordbox_db_stage, stage_rekordbox_db_operations


class RekordboxDbStageTests(unittest.TestCase):
    @requires_rekordbox_backend
    def test_stage_and_install_encrypted_rekordbox_db_update(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            assert_plain_sqlite_rejects(self, fixture.encrypted_db)
            ops = _write_update_ops(tmp, "New Title")

            with rekordbox_not_running():
                stage = stage_rekordbox_db_operations(fixture.encrypted_db, ops, tmp / "stage")
                staged = read_encrypted_master_copy(stage.staged_db, tmp / "copied-stage-master.db")
                before_install = read_encrypted_library(fixture.encrypted_db)
                report = install_rekordbox_db_stage(
                    tmp / "stage", fixture.encrypted_db, confirm_token=stage.install_token, process_lines=()
                )
                installed = read_encrypted_library(fixture.encrypted_db)

        self.assertEqual(staged.tracks[0].name, "New Title")
        self.assertEqual(before_install.tracks[0].name, "Track One")
        self.assertTrue(report["passed"])
        self.assertEqual(installed.tracks[0].name, "New Title")

    @requires_rekordbox_backend
    def test_plain_sqlite_fixture_is_rejected_by_plain_sqlite_probe_when_encrypted(self):
        with TemporaryDirectory() as tmpdir:
            fixture = generate_encrypted_rekordbox_fixture(Path(tmpdir) / "master.db")
            assert_plain_sqlite_rejects(self, fixture.encrypted_db)

    @requires_rekordbox_backend
    def test_install_refuses_when_live_db_changed_after_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            ops = _write_update_ops(tmp, "New Title")
            with rekordbox_not_running():
                stage = stage_rekordbox_db_operations(fixture.encrypted_db, ops, tmp / "stage")
            fixture.encrypted_db.write_bytes(fixture.encrypted_db.read_bytes() + b"changed")

            with self.assertRaises(RuntimeError):
                install_rekordbox_db_stage(
                    tmp / "stage", fixture.encrypted_db, confirm_token=stage.install_token, process_lines=()
                )

    @requires_rekordbox_backend
    def test_install_refuses_when_rekordbox_process_is_running(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            ops = _write_update_ops(tmp, "New Title")
            with rekordbox_not_running():
                stage = stage_rekordbox_db_operations(fixture.encrypted_db, ops, tmp / "stage")

            with self.assertRaises(RuntimeError):
                install_rekordbox_db_stage(
                    tmp / "stage",
                    fixture.encrypted_db,
                    confirm_token=stage.install_token,
                    process_lines=("123 rekordbox",),
                )

    @requires_rekordbox_backend
    def test_zero_row_update_refuses_to_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            ops = tmp / "ops.json"
            ops.write_text(
                json.dumps(
                    {
                        "operations": [
                            {
                                "operation": "update",
                                "table": "djmdContent",
                                "values": {"Title": "New Title"},
                                "where": {"ID": "999"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "matched 0 rows"), rekordbox_not_running():
                stage_rekordbox_db_operations(fixture.encrypted_db, ops, tmp / "stage")


def _write_update_ops(tmp: Path, title: str) -> Path:
    ops = tmp / "ops.json"
    ops.write_text(
        json.dumps(
            {
                "operations": [
                    {
                        "operation": "update",
                        "table": "djmdContent",
                        "values": {"Title": title},
                        "where": {"ID": "1"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return ops


if __name__ == "__main__":
    unittest.main()
