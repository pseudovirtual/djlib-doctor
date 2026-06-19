import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from tests.helpers import make_rekordbox_import_db, make_serato_root
from tests.support.rekordbox_encrypted_fixture import requires_rekordbox_backend

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, write_config
from djlib_doctor.rekordbox_xml import RekordboxLibrary, Track
from djlib_doctor.serato_tlv import record, text

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class DoctorTests(unittest.TestCase):
    def test_doctor_detects_and_checks_rekordbox_and_serato(self):
        with TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            desktop = home / "Desktop"
            serato = home / "Music" / "_Serato_"
            desktop.mkdir(parents=True)
            serato.mkdir(parents=True)
            (desktop / "rekordbox.xml").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            make_serato_root(serato / "root.sqlite")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(home)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox XML: PASS", output)
        self.assertIn("Serato root.sqlite: PASS", output)
        self.assertIn("Punch list:", output)
        self.assertIn("djlib-doctor snapshot --rekordbox-xml", output)
        self.assertIn("djlib-doctor inspect serato --library-dir", output)

    def test_doctor_prints_detect_command_when_nothing_found(self):
        with TemporaryDirectory() as tmpdir:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(Path(tmpdir) / "home")])

        self.assertEqual(exit_code, 0)
        self.assertIn("No Rekordbox or Serato libraries found", stdout.getvalue())
        self.assertIn("djlib-doctor detect", stdout.getvalue())

    @requires_rekordbox_backend
    def test_doctor_checks_configured_rekordbox_db_and_serato_database_v2(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            serato = tmp / "_Serato_"
            config_path = tmp / "djlib-doctor.json"
            serato.mkdir()
            make_rekordbox_import_db(db)
            _write_serato_database_v2(serato / "database V2")
            write_config(config_path, default_config(rekordbox_db=db, serato_music_dir=serato))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(tmp / "empty-home"), "--config", str(config_path)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox DB: PASS", output)
        self.assertIn("Serato database V2: PASS", output)

    @requires_rekordbox_backend
    def test_doctor_reports_configured_encrypted_rekordbox_db_clearly(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            config_path = tmp / "djlib-doctor.json"
            db.write_bytes(b"SQLCipher encrypted Rekordbox database placeholder")
            write_config(config_path, default_config(rekordbox_db=db))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(tmp / "empty-home"), "--config", str(config_path)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox DB: FAIL", output)
        self.assertTrue("SQLCipher backend is unavailable" in output or "could not unlock" in output)

    def test_doctor_can_check_rekordbox_db_via_pyrekordbox_reader(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            config_path = tmp / "djlib-doctor.json"
            db.write_bytes(b"encrypted placeholder")
            write_config(config_path, default_config(rekordbox_db=db))
            library = RekordboxLibrary(
                tracks=(Track("1", "Track One", "Artist One", None, "unknown", None, "AIFF"),),
                playlist_refs=(),
            )
            stdout = io.StringIO()

            with mock.patch("djlib_doctor.doctor.read_rekordbox_master_db", return_value=library):
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(["doctor", "--home", str(tmp / "empty-home"), "--config", str(config_path)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox DB: PASS", output)

    def test_doctor_uses_shared_rekordbox_db_reader_for_plain_db(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db = tmp / "master.db"
            config_path = tmp / "djlib-doctor.json"
            make_rekordbox_import_db(db)
            write_config(config_path, default_config(rekordbox_db=db))
            library = RekordboxLibrary(
                tracks=(Track("1", "Track One", "Artist One", None, "unknown", None, "AIFF"),),
                playlist_refs=(),
            )
            stdout = io.StringIO()

            with mock.patch("djlib_doctor.doctor.read_rekordbox_master_db", return_value=library) as reader:
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(["doctor", "--home", str(tmp / "empty-home"), "--config", str(config_path)])

        self.assertEqual(exit_code, 0)
        reader.assert_called_once_with(db)
        self.assertIn("Rekordbox DB: PASS", stdout.getvalue())

    def test_doctor_json_outputs_machine_readable_report(self):
        with TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            desktop = home / "Desktop"
            desktop.mkdir(parents=True)
            (desktop / "rekordbox.xml").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(home), "--json"])

        report = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(report["schema_version"], "1.0")
        self.assertEqual(report["checks"][0]["label"], "Rekordbox XML")
        self.assertEqual(report["checks"][0]["status"], "PASS")


def _write_serato_database_v2(path: Path) -> None:
    # Real database V2 otrk fields use pfil/tsng/tart, not crate-style ptrk/pnam/part.
    path.write_bytes(
        b"".join(
            (
                record("vrsn", text("1.0/Serato ScratchLive Database")),
                record(
                    "otrk",
                    b"".join(
                        (
                            record("pfil", text("Music/Track One.aiff")),
                            record("tsng", text("Track One")),
                            record("tart", text("Artist One")),
                        )
                    ),
                ),
            )
        )
    )


if __name__ == "__main__":
    unittest.main()
