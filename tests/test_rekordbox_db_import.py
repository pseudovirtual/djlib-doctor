import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.helpers import make_rekordbox_import_db
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
from tests.support.rekordbox_import_fixture import (
    make_serato_root,
    make_serato_to_rekordbox_manifest,
    make_unsupported_rekordbox_db,
)

from djlib_doctor.cli import main
from djlib_doctor.rekordbox_db_import import build_rekordbox_db_import_operations
from djlib_doctor.rekordbox_db_stage import install_rekordbox_db_stage, stage_rekordbox_db_import
from djlib_doctor.serato_crate import write_serato_crate


class RekordboxDbImportTests(unittest.TestCase):
    @requires_rekordbox_backend
    def test_stage_and_install_encrypted_rekordbox_db_import_from_serato_port_manifest(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            assert_plain_sqlite_rejects(self, fixture.encrypted_db)
            manifest = tmp / "port-manifest.json"
            make_serato_to_rekordbox_manifest(manifest)

            with rekordbox_not_running():
                stage = stage_rekordbox_db_import(fixture.encrypted_db, manifest, tmp / "stage")
                report = install_rekordbox_db_stage(
                    tmp / "stage", fixture.encrypted_db, confirm_token=stage.install_token, process_lines=()
                )
            ops = json.loads((tmp / "stage" / "rekordbox-db-import-operations.json").read_text(encoding="utf-8"))
            staged = read_encrypted_master_copy(stage.staged_db, tmp / "copied-import-master.db")
            installed = read_encrypted_library(fixture.encrypted_db)

        self.assertEqual(ops["summary"], {"insert": 2, "update": 1})
        self.assertTrue(report["passed"])
        self.assertEqual(staged.tracks[0].name, "Track One")
        self.assertEqual(installed.tracks[0].name, "Track One")
        self.assertGreaterEqual(len(installed.tracks[0].cues), 2)

    @requires_rekordbox_backend
    def test_cli_stage_rekordbox_db_import_prints_install_token(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            manifest = tmp / "port-manifest.json"
            make_serato_to_rekordbox_manifest(manifest)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), rekordbox_not_running():
                exit_code = main(
                    [
                        "stage",
                        "rekordbox-db-import",
                        "--db",
                        str(fixture.encrypted_db),
                        "--port-manifest",
                        str(manifest),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox DB import stage written:", stdout.getvalue())
        self.assertIn("Install token: INSTALL_SQLITE_STAGE:", stdout.getvalue())

    @requires_rekordbox_backend
    def test_cli_migrate_serato_to_rb_can_stage_rekordbox_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            crate = tmp / "Test.crate"
            make_serato_root(library / "root.sqlite")
            write_serato_crate(crate, ("Music/Track One.aiff",))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout), rekordbox_not_running():
                exit_code = main(
                    [
                        "migrate",
                        "serato-to-rb",
                        "--serato-library-dir",
                        str(library),
                        "--crate",
                        str(crate),
                        "--collection-root",
                        "/Music",
                        "--out",
                        str(tmp / "out"),
                        "--stage-db",
                        "--rekordbox-db",
                        str(fixture.encrypted_db),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Rekordbox DB stage:", stdout.getvalue())
            self.assertTrue((tmp / "out" / "rekordbox-stage" / "rekordbox-db-stage-manifest.json").exists())

    def test_rekordbox_db_import_refuses_unsupported_schema(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            make_unsupported_rekordbox_db(db)
            make_serato_to_rekordbox_manifest(manifest)

            with self.assertRaises(ValueError):
                stage_rekordbox_db_import(db, manifest, tmp / "stage")

    def test_import_operations_use_real_djmdcue_fields(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            ops_path = tmp / "ops.json"
            make_rekordbox_import_db(db)
            make_serato_to_rekordbox_manifest(manifest)

            build_rekordbox_db_import_operations(db, manifest, ops_path)
            cue_ops = [
                operation
                for operation in json.loads(ops_path.read_text(encoding="utf-8"))["operations"]
                if operation["table"] == "djmdCue" and operation["operation"] == "insert"
            ]

        point, loop = (operation["values"] for operation in cue_ops)
        self.assertNotIn("HotCue", point)
        self.assertEqual(
            {key: point[key] for key in ("InMsec", "OutMsec", "Kind", "is_hot_cue", "is_memory_cue")},
            {"InMsec": 12345, "OutMsec": -1, "Kind": 1, "is_hot_cue": True, "is_memory_cue": False},
        )
        self.assertEqual(loop["Kind"], 2)
        self.assertEqual(loop["OutMsec"], 56000)

    @requires_rekordbox_backend
    def test_rekordbox_db_import_refuses_encrypted_sqlcipher_db_clearly(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            manifest = tmp / "port-manifest.json"
            db.write_bytes(b"SQLCipher encrypted Rekordbox database placeholder")
            make_serato_to_rekordbox_manifest(manifest)

            with self.assertRaisesRegex(ValueError, r"encrypted SQLCipher.*pyrekordbox/SQLCipher backend"):
                stage_rekordbox_db_import(db, manifest, tmp / "stage")

    @requires_rekordbox_backend
    def test_stage_rekordbox_db_import_updates_encrypted_db_fixture(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fixture = generate_encrypted_rekordbox_fixture(tmp / "master.db")
            manifest = tmp / "port-manifest.json"
            make_serato_to_rekordbox_manifest(manifest)

            with rekordbox_not_running():
                stage = stage_rekordbox_db_import(fixture.encrypted_db, manifest, tmp / "stage")
                library = read_encrypted_master_copy(stage.staged_db, tmp / "copied-import-stage-master.db")

        self.assertEqual(library.tracks[0].name, "Track One")
        self.assertEqual(library.tracks[0].cues[0].start, 12.345)
