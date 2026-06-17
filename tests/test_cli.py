from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest
from unittest import mock

from djlib_doctor.cli import main
from djlib_doctor import cli_read


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
                exit_code = main(["verify", str(FIXTURE), "--no-file-check", "--json", "--pretty", "--out", str(out_path)])

            data = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("Verification report written:", stdout.getvalue())
        self.assertEqual(data["status"], "pass")
