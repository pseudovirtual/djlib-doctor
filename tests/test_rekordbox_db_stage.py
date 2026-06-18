import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.support.rekordbox_encrypted_fixture import (
    SqlcipherUnavailable,
    generate_encrypted_rekordbox_fixture,
    rekordbox_public_sqlcipher_key,
)

from djlib_doctor.rekordbox_db_read import read_rekordbox_master_db
from djlib_doctor.rekordbox_db_stage import install_rekordbox_db_stage, stage_rekordbox_db_operations


class RekordboxDbStageTests(unittest.TestCase):
    def test_stage_and_install_rekordbox_db_update(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE tracks(id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO tracks(id, name) VALUES(1, 'Old')")
            conn.commit()
            conn.close()
            ops = tmp / "ops.json"
            ops.write_text(
                json.dumps(
                    {
                        "operations": [
                            {
                                "operation": "update",
                                "table": "tracks",
                                "values": {"name": "New"},
                                "where": {"id": 1},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stage = stage_rekordbox_db_operations(db, ops, tmp / "stage")
            report = install_rekordbox_db_stage(tmp / "stage", db, confirm_token=stage.install_token)
            conn = sqlite3.connect(db)
            try:
                value = conn.execute("SELECT name FROM tracks WHERE id = 1").fetchone()[0]
            finally:
                conn.close()

        self.assertTrue(report["passed"])
        self.assertEqual(value, "New")

    def test_install_refuses_when_live_db_changed_after_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE tracks(id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO tracks(id, name) VALUES(1, 'Old')")
            conn.commit()
            conn.close()
            ops = tmp / "ops.json"
            ops.write_text(
                json.dumps(
                    {
                        "operations": [
                            {
                                "operation": "update",
                                "table": "tracks",
                                "values": {"name": "New"},
                                "where": {"id": 1},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stage = stage_rekordbox_db_operations(db, ops, tmp / "stage")

            conn = sqlite3.connect(db)
            conn.execute("INSERT INTO tracks(id, name) VALUES(2, 'Later')")
            conn.commit()
            conn.close()

            with self.assertRaises(RuntimeError):
                install_rekordbox_db_stage(tmp / "stage", db, confirm_token=stage.install_token)

    def test_install_refuses_when_rekordbox_process_is_running(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE tracks(id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO tracks(id, name) VALUES(1, 'Old')")
            conn.commit()
            conn.close()
            ops = tmp / "ops.json"
            ops.write_text(
                json.dumps(
                    {
                        "operations": [
                            {
                                "operation": "update",
                                "table": "tracks",
                                "values": {"name": "New"},
                                "where": {"id": 1},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            stage = stage_rekordbox_db_operations(db, ops, tmp / "stage")

            with self.assertRaises(RuntimeError):
                install_rekordbox_db_stage(
                    tmp / "stage", db, confirm_token=stage.install_token, process_lines=("123 rekordbox",)
                )

    def test_stage_and_install_encrypted_rekordbox_db_update(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            try:
                from pyrekordbox.db6 import database

                fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            except (ImportError, SqlcipherUnavailable) as exc:
                self.skipTest(str(exc))
            ops = tmp / "ops.json"
            ops.write_text(
                json.dumps(
                    {
                        "operations": [
                            {
                                "operation": "update",
                                "table": "djmdContent",
                                "values": {"Title": "New Title"},
                                "where": {"ID": "1"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            original_get_pid = database.get_rekordbox_pid
            database.get_rekordbox_pid = lambda: 0
            try:
                stage = stage_rekordbox_db_operations(fixture.encrypted_db, ops, tmp / "stage")
                staged = read_rekordbox_master_db(stage.staged_db, key=rekordbox_public_sqlcipher_key())
                before_install = read_rekordbox_master_db(fixture.encrypted_db, key=rekordbox_public_sqlcipher_key())
                report = install_rekordbox_db_stage(
                    tmp / "stage", fixture.encrypted_db, confirm_token=stage.install_token, process_lines=()
                )
                installed = read_rekordbox_master_db(fixture.encrypted_db, key=rekordbox_public_sqlcipher_key())
            finally:
                database.get_rekordbox_pid = original_get_pid

        self.assertEqual(staged.tracks[0].name, "New Title")
        self.assertEqual(before_install.tracks[0].name, "Track One")
        self.assertTrue(report["passed"])
        self.assertEqual(installed.tracks[0].name, "New Title")


if __name__ == "__main__":
    unittest.main()
