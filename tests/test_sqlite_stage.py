from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest

from djlib_doctor.sqlite_stage import install_sqlite_stage, stage_sqlite_operations


class SqliteStageTests(unittest.TestCase):
    def test_stage_and_install_sqlite_update(self):
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

            stage = stage_sqlite_operations(db, ops, tmp / "stage", label="rekordbox")
            report = install_sqlite_stage(tmp / "stage", db, confirm_token=stage.install_token, label="rekordbox")
            conn = sqlite3.connect(db)
            try:
                value = conn.execute("SELECT name FROM tracks WHERE id = 1").fetchone()[0]
            finally:
                conn.close()

        self.assertTrue(report["passed"])
        self.assertEqual(value, "New")


if __name__ == "__main__":
    unittest.main()
