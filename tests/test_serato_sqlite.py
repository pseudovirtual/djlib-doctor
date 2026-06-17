import contextlib
import io
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.serato_sqlite import inspect_serato_root_sqlite, write_serato_inspection


def make_serato_root(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE serato(revision INTEGER NOT NULL DEFAULT 0);
            INSERT INTO serato(revision) VALUES(10);
            CREATE TABLE asset(id INTEGER PRIMARY KEY, portable_id TEXT, name TEXT);
            INSERT INTO asset(id, portable_id, name) VALUES(1, 'Music/Track.aiff', 'Track');
            CREATE TABLE container(id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO container(id, name) VALUES(3, 'Serato Library root');
            """
        )
        conn.commit()
    finally:
        conn.close()


class SeratoSqliteTests(unittest.TestCase):
    def test_inspect_serato_root_sqlite_reports_tables_and_fingerprint(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "root.sqlite"
            make_serato_root(root)

            inspection = inspect_serato_root_sqlite(root)
            data = inspection.to_dict()

        self.assertEqual(data["summary"]["tables"], 3)
        self.assertEqual(data["asset_identity"]["identity_field"], "asset.portable_id")
        self.assertEqual(data["asset_identity"]["assets_with_identity"], 1)
        self.assertEqual(data["asset_identity"]["duplicate_identity_values"], 0)
        self.assertEqual(len(inspection.schema_fingerprint), 64)
        self.assertIn("asset", {table.name for table in inspection.tables})

    def test_write_serato_inspection_writes_json(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "root.sqlite"
            make_serato_root(root)
            out_path = write_serato_inspection(inspect_serato_root_sqlite(root), Path(tmpdir) / "inspect")
            data = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(data["schema_version"], "1.0")
        self.assertIn("schema_fingerprint", data)

    def test_inspect_serato_cli_writes_report(self):
        with TemporaryDirectory() as tmpdir:
            library_dir = Path(tmpdir) / "Library"
            library_dir.mkdir()
            make_serato_root(library_dir / "root.sqlite")
            out_dir = Path(tmpdir) / "out"

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["inspect", "serato", "--library-dir", str(library_dir), "--out", str(out_dir)])

            data = json.loads((out_dir / "serato-inspection.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["summary"]["tables"], 3)
        self.assertIn("Serato inspection written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
