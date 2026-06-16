from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest

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


if __name__ == "__main__":
    unittest.main()
