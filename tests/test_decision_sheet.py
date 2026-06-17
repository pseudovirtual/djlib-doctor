import contextlib
import csv
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.decision_sheet import write_decision_sheet
from djlib_doctor.plan import build_missing_files_plan, write_plan
from djlib_doctor.snapshot import create_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class DecisionSheetTests(unittest.TestCase):
    def test_write_decision_sheet_adds_blank_human_columns(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            out_path = Path(tmpdir) / "decisions.csv"

            write_decision_sheet(report, out_path)

            with out_path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["plan_type"], "missing-files")
        self.assertIn("decision", rows[0])
        self.assertIn("notes", rows[0])
        self.assertEqual(rows[0]["decision"], "")

    def test_decision_sheet_cli_reads_plan_and_writes_csv(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            plan_path = Path(tmpdir) / "plan.json"
            out_path = Path(tmpdir) / "decisions.csv"
            write_plan(report, plan_path)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["decision-sheet", "--plan", str(plan_path), "--out", str(out_path)])
            out_exists = out_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(out_exists)
        self.assertIn("Decision sheet written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
