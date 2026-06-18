import contextlib
import io
import json
import sqlite3
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main


class RekordboxCleanupApplyTests(unittest.TestCase):
    def test_stage_reviewed_cleanup_apply_manifest_updates_rekordbox_path_only_in_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            _make_rekordbox_content_db(db)
            apply_manifest = tmp / "apply-manifest.json"
            _write_apply_manifest(apply_manifest, candidate_path="/Music/Clean/Track One.aiff")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "stage",
                        "rekordbox-db-apply",
                        "--db",
                        str(db),
                        "--apply-manifest",
                        str(apply_manifest),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )
            staged_row = _content_row(tmp / "stage" / "master.db")
            live_row_before_install = _content_row(db)
            token = json.loads((tmp / "stage" / "rekordbox-db-stage-manifest.json").read_text(encoding="utf-8"))[
                "install_token"
            ]

            install_exit = main(
                [
                    "install",
                    "rekordbox-db",
                    "--stage-dir",
                    str(tmp / "stage"),
                    "--db",
                    str(db),
                    "--confirm-token",
                    token,
                    "--skip-process-check",
                ]
            )
            live_row_after_install = _content_row(db)

        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox DB apply stage written:", stdout.getvalue())
        self.assertEqual(staged_row, ("/Music/Clean", "Track One.aiff"))
        self.assertEqual(live_row_before_install, ("/Music/Bad", "Track One.aiff"))
        self.assertEqual(install_exit, 0)
        self.assertEqual(live_row_after_install, ("/Music/Clean", "Track One.aiff"))


def _make_rekordbox_content_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE djmdContent(
                ID INTEGER PRIMARY KEY,
                FolderPath TEXT,
                FileNameL TEXT,
                Title TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO djmdContent(ID, FolderPath, FileNameL, Title) VALUES(1, '/Music/Bad', 'Track One.aiff', 'Track One')"
        )
        conn.commit()
    finally:
        conn.close()


def _write_apply_manifest(path: Path, candidate_path: str) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "mode": "dry_run_only",
                "source_plan_type": "missing-files",
                "operations": [
                    {
                        "review_id": "MISSING-FILES-0001",
                        "track_id": "1",
                        "source_path": "/Music/Bad/Track One.aiff",
                        "candidate_path": candidate_path,
                        "review_decision": "manual_match",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def _content_row(path: Path) -> tuple[str, str]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT FolderPath, FileNameL FROM djmdContent WHERE ID = 1").fetchone()
    finally:
        conn.close()


if __name__ == "__main__":
    unittest.main()
