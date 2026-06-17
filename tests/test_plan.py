import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.collision_policy import DuplicateCollisionPolicy
from djlib_doctor.plan import build_bad_paths_plan, build_cues_plan, build_duplicates_plan, build_missing_files_plan
from djlib_doctor.snapshot import create_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"
DUPLICATE_FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "duplicate_cue_survivor.xml"
POLICY_FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "duplicate_policy_collision.xml"
BAD_PATH_FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "bad_active_folder_reference.xml"


class PlanTests(unittest.TestCase):
    def test_missing_files_plan_uses_snapshot_missing_csv(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            self.assertEqual(report.plan_type, "missing-files")
            self.assertEqual(len(report.actions), 2)
            by_track = {action.track_id: action for action in report.actions}
            self.assertEqual(by_track["1"].action, "reacquire_or_manual_match_preserve_cues")
            self.assertEqual(by_track["2"].action, "review_remove_unreferenced_missing_record")
            self.assertTrue(by_track["1"].human_review_required)

    def test_missing_files_plan_finds_same_stem_inventory_candidate(self):
        with TemporaryDirectory() as tmpdir:
            music_root = Path(tmpdir) / "music"
            music_root.mkdir()
            (music_root / "djlib-doctor-fixture-missing.aiff").write_bytes(b"fixture")
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", music_root=music_root, check_files=True)
            report = build_missing_files_plan(snapshot.snapshot_path)
            missing_action = next(action for action in report.actions if action.track_id == "2")
            self.assertEqual(missing_action.action, "review_candidate_replacement")
            self.assertEqual(missing_action.confidence.value, "weak")
            self.assertIn("same_normalized_filename_stem", missing_action.evidence)

    def test_plan_cli_writes_and_explain_reads_plan(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", check_files=True)
            plan_path = Path(tmpdir) / "plan.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    ["plan", "missing-files", "--snapshot", str(snapshot.snapshot_path), "--out", str(plan_path)]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(plan_path.exists())
            data = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(data["plan_type"], "missing-files")
            explain_stdout = io.StringIO()
            with contextlib.redirect_stdout(explain_stdout):
                explain_exit = main(["explain", "--plan", str(plan_path)])
            self.assertEqual(explain_exit, 0)
            self.assertIn("djlib-doctor plan: missing-files", explain_stdout.getvalue())

    def test_duplicates_plan_keeps_cued_survivor(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(DUPLICATE_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            report = build_duplicates_plan(snapshot.snapshot_path)
            self.assertEqual(report.plan_type, "duplicates")
            self.assertEqual(len(report.actions), 2)
            by_track = {action.track_id: action for action in report.actions}
            self.assertEqual(by_track["22"].action, "keep_duplicate_survivor")
            self.assertEqual(by_track["21"].action, "review_remove_duplicate_later")
            self.assertEqual(by_track["21"].metadata["recommended_survivor_track_id"], "22")

    def test_duplicates_plan_cli_writes_plan(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(DUPLICATE_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            plan_path = Path(tmpdir) / "duplicates.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    ["plan", "duplicates", "--snapshot", str(snapshot.snapshot_path), "--out", str(plan_path)]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(plan_path.exists())
            self.assertIn("djlib-doctor plan: duplicates", stdout.getvalue())

    def test_duplicates_plan_quality_policy_can_choose_better_file(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(POLICY_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            cue_safe = build_duplicates_plan(snapshot.snapshot_path)
            quality = build_duplicates_plan(snapshot.snapshot_path, collision_policy=DuplicateCollisionPolicy.QUALITY)
        cue_safe_survivor = next(action for action in cue_safe.actions if action.action == "keep_duplicate_survivor")
        quality_survivor = next(action for action in quality.actions if action.action == "keep_duplicate_survivor")
        self.assertEqual(cue_safe_survivor.track_id, "31")
        self.assertEqual(quality_survivor.track_id, "32")
        self.assertEqual(quality_survivor.metadata["collision_policy"], "quality")

    def test_duplicates_plan_keep_both_policy_does_not_recommend_removal(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(POLICY_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            report = build_duplicates_plan(snapshot.snapshot_path, collision_policy=DuplicateCollisionPolicy.KEEP_BOTH)
        self.assertEqual({action.action for action in report.actions}, {"keep_duplicate_record"})
        self.assertTrue(all(action.metadata["collision_policy"] == "keep-both" for action in report.actions))

    def test_duplicates_plan_cli_accepts_collision_policy(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(POLICY_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            plan_path = Path(tmpdir) / "duplicates-quality.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "plan",
                        "duplicates",
                        "--snapshot",
                        str(snapshot.snapshot_path),
                        "--out",
                        str(plan_path),
                        "--collision-policy",
                        "quality",
                    ]
                )
            data = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(exit_code, 0)
        self.assertIn("djlib-doctor plan: duplicates", stdout.getvalue())
        self.assertEqual(data["actions"][0]["metadata"]["collision_policy"], "quality")

    def test_cues_plan_uses_compare_issues(self):
        report = build_cues_plan(
            FIXTURE, Path(__file__).parent / "fixtures" / "rekordbox" / "final_missing_material.xml"
        )
        self.assertEqual(report.plan_type, "cues")
        actions = {action.action for action in report.actions}
        self.assertIn("review_add_or_preserve_missing_cue", actions)
        self.assertIn("review_hotcue_regression", actions)

    def test_cues_plan_cli_writes_plan(self):
        with TemporaryDirectory() as tmpdir:
            plan_path = Path(tmpdir) / "cues.json"
            final_xml = Path(__file__).parent / "fixtures" / "rekordbox" / "final_missing_material.xml"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    ["plan", "cues", "--baseline", str(FIXTURE), "--final", str(final_xml), "--out", str(plan_path)]
                )
            self.assertEqual(exit_code, 0)
            self.assertTrue(plan_path.exists())
            self.assertIn("djlib-doctor plan: cues", stdout.getvalue())

    def test_bad_paths_plan_flags_active_bad_folder_reference(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(BAD_PATH_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            report = build_bad_paths_plan(snapshot.snapshot_path)
            self.assertEqual(report.plan_type, "bad-paths")
            self.assertEqual(len(report.actions), 1)
            action = report.actions[0]
            self.assertEqual(action.track_id, "10")
            self.assertEqual(action.action, "review_bad_active_path_before_cleanup")
            self.assertEqual(action.confidence.value, "unsafe")
            self.assertIn("bad_path_marker:bad-folder", action.evidence)
            self.assertEqual(action.metadata["playlist_count"], 1)

    def test_bad_paths_plan_cli_accepts_custom_marker(self):
        with TemporaryDirectory() as tmpdir:
            snapshot = create_snapshot(BAD_PATH_FIXTURE, Path(tmpdir) / "snapshot", check_files=False)
            plan_path = Path(tmpdir) / "bad-paths.json"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "plan",
                        "bad-paths",
                        "--snapshot",
                        str(snapshot.snapshot_path),
                        "--out",
                        str(plan_path),
                        "--marker",
                        "clean",
                    ]
                )
            data = json.loads(plan_path.read_text(encoding="utf-8"))
            plan_exists = plan_path.exists()
        self.assertEqual(exit_code, 0)
        self.assertTrue(plan_exists)
        self.assertIn("djlib-doctor plan: bad-paths", stdout.getvalue())
        self.assertEqual(data["summary"]["actions"], 1)
        self.assertEqual(data["actions"][0]["track_id"], "11")


if __name__ == "__main__":
    unittest.main()
