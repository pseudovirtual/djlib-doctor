from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.apply_manifest import build_apply_manifest
from djlib_doctor.cli import main
from djlib_doctor.plan import build_missing_files_plan, write_plan
from djlib_doctor.reviewer import load_review_log, run_interactive_review
from djlib_doctor.snapshot import create_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class ApplyManifestTests(unittest.TestCase):
    def test_apply_manifest_is_dry_run_only(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            manifest = build_apply_manifest(report)
            data = manifest.to_dict()

        self.assertEqual(data["mode"], "dry_run_only")
        self.assertFalse(data["safety"]["applies_changes"])
        self.assertTrue(data["safety"]["requires_explicit_user_approval"])
        self.assertEqual(data["summary"]["operations"], 2)
        self.assertEqual(data["operations"][0]["status"], "not_applied")

    def test_apply_manifest_cli_writes_json(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            plan_path = Path(tmpdir) / "plan.json"
            manifest_path = Path(tmpdir) / "apply-manifest.json"
            write_plan(report, plan_path)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["apply-manifest", "--plan", str(plan_path), "--out", str(manifest_path)])

            data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["mode"], "dry_run_only")
        self.assertIn("Dry-run apply manifest written:", stdout.getvalue())

    def test_apply_manifest_can_ingest_review_log(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            review_path = Path(tmpdir) / "review.json"
            answers = iter(["1", "Approved reacquire", "q"])
            run_interactive_review(
                report,
                review_path,
                input_func=lambda prompt: next(answers),
                output=io.StringIO(),
            )

            manifest = build_apply_manifest(report, review_log=load_review_log(review_path), only_reviewed=True)
            data = manifest.to_dict()

        self.assertEqual(data["summary"]["operations"], 1)
        self.assertEqual(data["operations"][0]["review_decision"], "reacquire")
        self.assertEqual(data["operations"][0]["review_notes"], "Approved reacquire")

    def test_apply_manifest_cli_accepts_review_log(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            plan_path = Path(tmpdir) / "plan.json"
            review_path = Path(tmpdir) / "review.json"
            manifest_path = Path(tmpdir) / "apply-manifest.json"
            write_plan(report, plan_path)
            answers = iter(["1", "Approved", "q"])
            run_interactive_review(
                report,
                review_path,
                input_func=lambda prompt: next(answers),
                output=io.StringIO(),
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "apply-manifest",
                        "--plan",
                        str(plan_path),
                        "--review-log",
                        str(review_path),
                        "--only-reviewed",
                        "--out",
                        str(manifest_path),
                    ]
                )

            data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["summary"]["operations"], 1)
        self.assertEqual(data["operations"][0]["review_decision"], "reacquire")
        self.assertIn("Dry-run apply manifest written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
