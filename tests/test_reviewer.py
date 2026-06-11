from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from djlib_doctor.cli import main
from djlib_doctor.plan import build_missing_files_plan
from djlib_doctor.plan import write_plan
from djlib_doctor.reviewer import load_review_log, run_interactive_review
from djlib_doctor.snapshot import create_snapshot


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class ReviewerTests(unittest.TestCase):
    def test_interactive_review_records_decisions_incrementally(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            out_path = Path(tmpdir) / "review-decisions.json"
            answers = iter(["1", "Need to buy it again", "s"])

            decisions = run_interactive_review(
                report,
                out_path,
                input_func=lambda prompt: next(answers),
                output=io.StringIO(),
            )
            data = json.loads(out_path.read_text(encoding="utf-8"))
            loaded = load_review_log(out_path)

        self.assertEqual(len(decisions), 2)
        self.assertEqual(decisions[0].decision, "reacquire")
        self.assertEqual(decisions[0].notes, "Need to buy it again")
        self.assertEqual(decisions[1].decision, "skip")
        self.assertEqual(data["summary"]["decisions"], 2)
        self.assertEqual(loaded.decisions[0].review_id, "MISSING-FILES-0001")

    def test_review_cli_records_decision_log(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            plan_path = Path(tmpdir) / "plan.json"
            out_path = Path(tmpdir) / "review.json"
            write_plan(report, plan_path)

            stdout = io.StringIO()
            with patch("sys.stdin", io.StringIO("1\nApproved\nq\n")):
                with contextlib.redirect_stdout(stdout):
                    exit_code = main(["review", "--plan", str(plan_path), "--out", str(out_path)])

            data = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["decisions"][0]["decision"], "reacquire")
        self.assertIn("Review decisions written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
