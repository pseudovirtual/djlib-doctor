import contextlib
import io
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
    SqlcipherUnavailable,
    generate_encrypted_rekordbox_fixture,
    skip_or_fail_for_missing_encrypted_backend,
)

from djlib_doctor.cli import main


class RekordboxMoveTests(unittest.TestCase):
    def test_stage_and_install_moves_file_and_updates_encrypted_db_path(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Old Folder" / "Track One.aiff"
            target = tmp / "New Folder" / "Track One Renamed.aiff"
            try:
                fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            except SqlcipherUnavailable as exc:
                skip_or_fail_for_missing_encrypted_backend(self, exc)
            assert_plain_sqlite_rejects(self, fixture.encrypted_db)
            source.parent.mkdir()
            source.write_bytes(b"audio")
            operations = _write_operations(tmp, source, target)

            with contextlib.redirect_stdout(io.StringIO()), rekordbox_not_running():
                stage_exit = main(
                    [
                        "stage",
                        "rekordbox-move",
                        "--db",
                        str(fixture.encrypted_db),
                        "--operations",
                        str(operations),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )
            manifest = json.loads((tmp / "stage" / "rekordbox-move-stage-manifest.json").read_text())
            staged_library = read_encrypted_master_copy(tmp / "stage" / "master.db", tmp / "copied-move-master.db")
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
                rekordbox_not_running(),
            ):
                install_exit = main(
                    [
                        "install",
                        "rekordbox-move",
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--db",
                        str(fixture.encrypted_db),
                        "--confirm-token",
                        manifest["install_token"],
                        "--skip-process-check",
                    ]
                )
            source_exists = source.exists()
            target_bytes = target.read_bytes()
            installed_library = read_encrypted_library(fixture.encrypted_db)
            report_exists = (tmp / "stage" / "rekordbox-move-install-report.json").is_file()

        self.assertEqual(stage_exit, 0)
        self.assertEqual(install_exit, 0)
        self.assertEqual(staged_library.tracks[0].path, target)
        self.assertFalse(source_exists)
        self.assertEqual(target_bytes, b"audio")
        self.assertEqual(installed_library.tracks[0].path, target)
        self.assertTrue(report_exists)

    def test_install_refuses_when_source_hash_changed_after_staging(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "Old Folder" / "Track One.aiff"
            target = tmp / "New Folder" / "Track One Renamed.aiff"
            try:
                fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            except SqlcipherUnavailable as exc:
                skip_or_fail_for_missing_encrypted_backend(self, exc)
            source.parent.mkdir()
            source.write_bytes(b"audio")
            operations = _write_operations(tmp, source, target)

            with contextlib.redirect_stdout(io.StringIO()), rekordbox_not_running():
                self.assertEqual(
                    main(
                        [
                            "stage",
                            "rekordbox-move",
                            "--db",
                            str(fixture.encrypted_db),
                            "--operations",
                            str(operations),
                            "--stage-dir",
                            str(tmp / "stage"),
                        ]
                    ),
                    0,
                )
            source.write_bytes(b"changed")
            manifest = json.loads((tmp / "stage" / "rekordbox-move-stage-manifest.json").read_text())
            with (
                contextlib.redirect_stdout(io.StringIO()),
                contextlib.redirect_stderr(io.StringIO()),
                rekordbox_not_running(),
            ):
                install_exit = main(
                    [
                        "install",
                        "rekordbox-move",
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--db",
                        str(fixture.encrypted_db),
                        "--confirm-token",
                        manifest["install_token"],
                        "--skip-process-check",
                    ]
                )
            source_exists = source.exists()
            target_exists = target.exists()
            installed_library = read_encrypted_library(fixture.encrypted_db)

        self.assertEqual(install_exit, 3)
        self.assertTrue(source_exists)
        self.assertFalse(target_exists)
        self.assertNotEqual(installed_library.tracks[0].path, target)


def _write_operations(tmp: Path, source: Path, target: Path) -> Path:
    operations = tmp / "move.json"
    operations.write_text(
        json.dumps({"operations": [{"track_id": "1", "source": str(source), "target": str(target)}]}),
        encoding="utf-8",
    )
    return operations
