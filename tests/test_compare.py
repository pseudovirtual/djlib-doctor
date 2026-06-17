import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.compare import compare_exports

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"
FINAL_MISSING = Path(__file__).parent / "fixtures" / "rekordbox" / "final_missing_material.xml"
BAD_PATH_FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "bad_active_folder_reference.xml"


class CompareTests(unittest.TestCase):
    def test_compare_identical_exports_passes(self):
        report = compare_exports(FIXTURE, FIXTURE)

        self.assertTrue(report.passed)
        self.assertEqual(report.issues, ())

    def test_compare_detects_missing_material_and_cue_regression(self):
        report = compare_exports(FIXTURE, FINAL_MISSING)

        self.assertFalse(report.passed)
        codes = {issue.code for issue in report.issues}
        self.assertIn("missing_material", codes)
        self.assertIn("cue_not_covered", codes)
        self.assertIn("hotcue_regression", codes)
        self.assertIn("playlist_order_or_entry_diff", codes)

    def test_compare_detects_final_bad_paths(self):
        report = compare_exports(BAD_PATH_FIXTURE, BAD_PATH_FIXTURE)

        self.assertFalse(report.passed)
        self.assertIn("final_bad_path", {issue.code for issue in report.issues})

    def test_compare_can_check_final_missing_local_files(self):
        report = compare_exports(FIXTURE, FIXTURE, check_files=True)

        self.assertFalse(report.passed)
        self.assertIn("final_missing_local_file", {issue.code for issue in report.issues})

    def test_compare_cli_writes_json_report(self):
        with TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "compare.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "compare",
                        "exports",
                        "--baseline",
                        str(FIXTURE),
                        "--final",
                        str(FIXTURE),
                        "--out",
                        str(out_path),
                        "--json",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(out_path.exists())
            data = json.loads(stdout.getvalue())
            self.assertEqual(data["status"], "pass")
            self.assertEqual(data["schema_version"], "1.0")

    def test_compare_cli_check_files_adds_missing_status(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            exit_code = main(
                ["compare", "exports", "--baseline", str(FIXTURE), "--final", str(FIXTURE), "--check-files", "--json"]
            )

        data = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 1)
        self.assertEqual(data["summary"]["final_missing_local_file"], 2)


if __name__ == "__main__":
    unittest.main()
