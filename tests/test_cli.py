import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from djlib_doctor import cli_read
from djlib_doctor.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class CliTests(unittest.TestCase):
    def test_self_test_command_passes(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["self-test"])

        self.assertEqual(exit_code, 0)
        self.assertIn("djlib-doctor self-test: PASS", stdout.getvalue())

    def test_self_test_does_not_require_repo_tests_fixture(self):
        real_parse = cli_read.parse_rekordbox_xml

        def parse_without_repo_fixture(path):
            if "/tests/fixtures/" in str(path):
                raise FileNotFoundError(path)
            return real_parse(path)

        stdout = io.StringIO()
        with mock.patch("djlib_doctor.cli_read.parse_rekordbox_xml", side_effect=parse_without_repo_fixture):
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["self-test"])

        self.assertEqual(exit_code, 0)
        self.assertIn("djlib-doctor self-test: PASS", stdout.getvalue())

    def test_verify_returns_input_error_for_malformed_xml(self):
        with TemporaryDirectory() as tmpdir:
            xml_path = Path(tmpdir) / "bad.xml"
            xml_path.write_text("<DJ_PLAYLISTS><COLLECTION>", encoding="utf-8")

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["verify", str(xml_path)])

        self.assertEqual(exit_code, 3)
        self.assertIn("djlib-doctor verification: ERROR", stderr.getvalue())

    def test_verify_json_outputs_machine_readable_report(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["verify", str(FIXTURE), "--no-file-check", "--json"])

        data = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["status"], "pass")
        self.assertEqual(data["counts"]["collection_tracks"], 3)
        self.assertEqual(data["source"]["path"], str(FIXTURE))
        self.assertFalse(data["source"]["check_files"])
        self.assertIn("next_actions", data)

    def test_verify_schema_version_does_not_require_xml(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(["verify", "--schema-version"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "1.0")

    def test_verify_writes_requested_output_file(self):
        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "verification.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    ["verify", str(FIXTURE), "--no-file-check", "--json", "--pretty", "--out", str(out_path)]
                )

            data = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("Verification report written:", stdout.getvalue())
        self.assertEqual(data["status"], "pass")

    def test_verify_uses_configured_rekordbox_xml_when_arg_is_omitted(self):
        with TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "config.json"
            config.write_text(json.dumps({"primary": "rekordbox", "rekordbox_xml": str(FIXTURE)}), encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["verify", "--config", str(config), "--no-file-check", "--json"])

        data = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["source"]["path"], str(FIXTURE))

    def test_verify_detects_rekordbox_xml_when_arg_and_config_are_omitted(self):
        with TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            desktop = home / "Desktop"
            desktop.mkdir(parents=True)
            detected_xml = desktop / "rekordbox.xml"
            detected_xml.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["verify", "--home", str(home), "--no-file-check", "--json"])

        data = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(data["source"]["path"], str(detected_xml))

    def test_verify_rejects_serato_primary_with_clear_message(self):
        with TemporaryDirectory() as tmpdir:
            config = Path(tmpdir) / "config.json"
            config.write_text(json.dumps({"primary": "serato"}), encoding="utf-8")

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                exit_code = main(["verify", "--config", str(config)])

        self.assertEqual(exit_code, 3)
        self.assertIn("verify currently supports Rekordbox XML", stderr.getvalue())
