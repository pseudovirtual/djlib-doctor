from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import sqlite3
import unittest

from djlib_doctor.cli import main
from djlib_doctor.port_rekordbox_serato import build_rekordbox_to_serato_plan, write_rekordbox_to_serato_plan
from djlib_doctor.serato_crate import read_serato_crate
from djlib_doctor.serato_stage import (
    install_serato_stage,
    stage_serato_from_port_manifest,
    verify_serato_stage,
)
from helpers import make_serato_root


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class SeratoStageTests(unittest.TestCase):
    def test_stage_from_port_manifest_modifies_only_stage_copy(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            live_library = tmp / "Library"
            live_music = tmp / "_Serato_"
            live_library.mkdir()
            live_music.mkdir()
            make_serato_root(live_library / "root.sqlite")
            port_dir = tmp / "port"
            port_outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                port_dir,
            )

            stage_report = stage_serato_from_port_manifest(
                Path(port_outputs["manifest"]),
                live_library,
                live_music,
                tmp / "stage",
            )

            live_conn = sqlite3.connect(live_library / "root.sqlite")
            stage_conn = sqlite3.connect(stage_report.staged_root_sqlite)
            try:
                self.assertEqual(live_conn.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 0)
                self.assertEqual(stage_conn.execute("SELECT COUNT(*) FROM asset").fetchone()[0], 1)
                self.assertEqual(stage_conn.execute("SELECT COUNT(*) FROM container_asset").fetchone()[0], 1)
            finally:
                live_conn.close()
                stage_conn.close()
            self.assertTrue(stage_report.stage_manifest_path.is_file())
            self.assertTrue(stage_report.install_token.startswith("INSTALL_SERATO_STAGE:"))
            self.assertTrue(verify_serato_stage(tmp / "stage").passed)

    def test_install_stage_requires_confirmation_token_and_hash_verifies(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            live_library = tmp / "Library"
            live_music = tmp / "_Serato_"
            live_library.mkdir()
            live_music.mkdir()
            make_serato_root(live_library / "root.sqlite")
            port_outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )
            stage_report = stage_serato_from_port_manifest(Path(port_outputs["manifest"]), live_library, live_music, tmp / "stage")

            with self.assertRaises(ValueError):
                install_serato_stage(tmp / "stage", live_library, live_music, confirm_token="wrong", process_lines=())

            install_report = install_serato_stage(
                tmp / "stage",
                live_library,
                live_music,
                confirm_token=stage_report.install_token,
                process_lines=(),
            )

            self.assertTrue(install_report.passed)
            self.assertTrue((live_music / "Subcrates" / "RB - ROOT - Fixture Playlist.crate").is_file())
            self.assertEqual(read_serato_crate(live_music / "Subcrates" / "RB - ROOT - Fixture Playlist.crate").tracks[0], "private/tmp/djlib-doctor-fixture-present.aiff")

    def test_install_stage_refuses_when_live_root_changed_after_stage(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            live_library = tmp / "Library"
            live_music = tmp / "_Serato_"
            live_library.mkdir()
            live_music.mkdir()
            make_serato_root(live_library / "root.sqlite")
            port_outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )
            stage_report = stage_serato_from_port_manifest(Path(port_outputs["manifest"]), live_library, live_music, tmp / "stage")
            conn = sqlite3.connect(live_library / "root.sqlite")
            try:
                conn.execute("UPDATE serato SET revision = revision + 1")
                conn.commit()
            finally:
                conn.close()

            with self.assertRaises(RuntimeError):
                install_serato_stage(
                    tmp / "stage",
                    live_library,
                    live_music,
                    confirm_token=stage_report.install_token,
                    process_lines=(),
                )

    def test_install_stage_refuses_when_serato_process_is_running(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            live_library = tmp / "Library"
            live_music = tmp / "_Serato_"
            live_library.mkdir()
            live_music.mkdir()
            make_serato_root(live_library / "root.sqlite")
            port_outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )
            stage_report = stage_serato_from_port_manifest(Path(port_outputs["manifest"]), live_library, live_music, tmp / "stage")

            with self.assertRaises(RuntimeError):
                install_serato_stage(
                    tmp / "stage",
                    live_library,
                    live_music,
                    confirm_token=stage_report.install_token,
                    process_lines=("123 Serato DJ Pro",),
                )

    def test_stage_and_install_cli_are_agent_friendly(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            live_library = tmp / "Library"
            live_music = tmp / "_Serato_"
            live_library.mkdir()
            live_music.mkdir()
            make_serato_root(live_library / "root.sqlite")
            port_outputs = write_rekordbox_to_serato_plan(
                build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist"),
                tmp / "port",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "stage",
                        "serato",
                        "--port-manifest",
                        str(port_outputs["manifest"]),
                        "--serato-library-dir",
                        str(live_library),
                        "--serato-music-dir",
                        str(live_music),
                        "--stage-dir",
                        str(tmp / "stage"),
                    ]
                )
            token = json.loads((tmp / "stage" / "serato-stage-manifest.json").read_text(encoding="utf-8"))["install_token"]

            with contextlib.redirect_stdout(io.StringIO()):
                install_exit = main(
                    [
                        "install",
                        "serato-stage",
                        "--stage-dir",
                        str(tmp / "stage"),
                        "--serato-library-dir",
                        str(live_library),
                        "--serato-music-dir",
                        str(live_music),
                        "--confirm-token",
                        token,
                        "--skip-process-check",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(install_exit, 0)
        self.assertIn("Serato stage written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
