from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.port_rekordbox_serato import (
    build_rekordbox_collection_to_serato_plan,
    build_rekordbox_to_serato_plan,
    build_rekordbox_to_serato_plans,
    build_rekordbox_track_to_serato_plan,
    serato_format_capability,
    verify_rekordbox_to_serato_plan,
    write_rekordbox_to_serato_plan,
)
from djlib_doctor.serato_crate import read_serato_crate


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class PortSeratoTests(unittest.TestCase):
    def test_build_rekordbox_to_serato_plan_maps_playlist_and_cues(self):
        plan = build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist", crate_prefix="RB - ")
        track = plan.tracks[0]
        intents = [intent.intent for intent in track.cue_intents]

        self.assertEqual(plan.target_crate_name, "RB - ROOT / Fixture Playlist")
        self.assertEqual(len(plan.tracks), 1)
        self.assertEqual(len(plan.skipped), 1)
        self.assertEqual(plan.summary["format_counts"]["aiff"], 1)
        self.assertEqual(plan.summary["cue_counts"]["raw_rekordbox_cue_rows"], 3)
        self.assertEqual(plan.summary["cue_counts"]["unique_track_cues"], 3)
        self.assertEqual(plan.summary["cue_counts"]["serato_writable_slots"], 4)
        self.assertIn("serato_hotcue", intents)
        self.assertIn("serato_saved_loop", intents)
        self.assertEqual(plan.skipped[0]["reason"], "not_local_file")

    def test_build_rekordbox_track_to_serato_plan_scopes_single_track(self):
        plan = build_rekordbox_track_to_serato_plan(FIXTURE, "1", transfer_mode="cues-only")

        self.assertEqual(plan.scope, "track")
        self.assertEqual(plan.transfer_mode, "cues-only")
        self.assertEqual(len(plan.tracks), 1)
        self.assertEqual(plan.tracks[0].source_id, "1")
        self.assertEqual(plan.to_dict()["transfer_mode"], "cues-only")

    def test_build_rekordbox_collection_to_serato_plan_skips_non_local_tracks(self):
        plan = build_rekordbox_collection_to_serato_plan(FIXTURE, transfer_mode="match-only")

        self.assertEqual(plan.scope, "collection")
        self.assertEqual(plan.transfer_mode, "match-only")
        self.assertEqual(plan.summary["tracks"], 2)
        self.assertEqual(len(plan.skipped), 1)

    def test_batch_plan_preserves_playlist_order_and_reports_name_warnings(self):
        plan = build_rekordbox_to_serato_plans(
            FIXTURE,
            ["ROOT / Fixture Playlist", " ROOT / Fixture Playlist "],
            crate_prefix="RB - ",
        )

        self.assertEqual([crate.source_playlist for crate in plan.crates], ["ROOT / Fixture Playlist", "ROOT / Fixture Playlist"])
        self.assertEqual(plan.summary["crates"], 2)
        self.assertEqual(plan.summary["tracks"], 2)
        self.assertIn("playlist_name_matched_after_trimming", plan.warnings[0]["code"])
        self.assertIn("target_crate_filename_collision", {warning["code"] for warning in plan.warnings})

    def test_serato_format_capability_describes_known_and_unknown_formats(self):
        self.assertEqual(serato_format_capability("/tmp/song.aiff")["cue_tags"], "aiff_id3_geob_markers2")
        self.assertEqual(serato_format_capability("/tmp/song.m4a")["cue_tags"], "mp4_freeform_markersv2")
        self.assertEqual(serato_format_capability("/tmp/song.flac")["status"], "future_uncertain")

    def test_verify_rekordbox_to_serato_plan_checks_crate_preview(self):
        with TemporaryDirectory() as tmpdir:
            plan = build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist")
            outputs = write_rekordbox_to_serato_plan(plan, Path(tmpdir))
            report = verify_rekordbox_to_serato_plan(Path(outputs["manifest"]), Path(outputs["crate_preview"]))

        self.assertTrue(report["passed"])
        self.assertEqual(report["checks"]["crate_track_order"], "passed")

    def test_write_rekordbox_to_serato_plan_writes_manifest_and_crate_preview(self):
        with TemporaryDirectory() as tmpdir:
            plan = build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist")
            outputs = write_rekordbox_to_serato_plan(plan, Path(tmpdir))
            manifest = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
            crate = read_serato_crate(Path(outputs["crate_preview"]))

        self.assertEqual(manifest["mode"], "dry_run_only")
        self.assertEqual(manifest["summary"]["tracks"], 1)
        self.assertEqual(len(crate.tracks), 1)

    def test_write_batch_plan_returns_crate_preview_paths_as_list(self):
        with TemporaryDirectory() as tmpdir:
            plan = build_rekordbox_to_serato_plans(FIXTURE, ["ROOT / Fixture Playlist"])
            outputs = write_rekordbox_to_serato_plan(plan, Path(tmpdir))

        self.assertIsInstance(outputs["crate_previews"], list)
        self.assertEqual(len(outputs["crate_previews"]), 1)

    def test_port_cli_writes_outputs(self):
        with TemporaryDirectory() as tmpdir:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "port",
                        "rb-to-serato",
                        "--rekordbox-xml",
                        str(FIXTURE),
                        "--playlist",
                        "ROOT / Fixture Playlist",
                        "--out",
                        tmpdir,
                    ]
                )

            manifest_path = Path(tmpdir) / "port-manifest.json"
            data = json.loads(manifest_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["target_platform"], "serato")
        self.assertIn("Serato crate preview written:", stdout.getvalue())

    def test_port_cli_accepts_track_scope_and_transfer_mode(self):
        with TemporaryDirectory() as tmpdir:
            exit_code = main(
                [
                    "port",
                    "rb-to-serato",
                    "--rekordbox-xml",
                    str(FIXTURE),
                    "--track-id",
                    "1",
                    "--transfer-mode",
                    "cues-only",
                    "--out",
                    tmpdir,
                ]
            )
            data = json.loads((Path(tmpdir) / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["scope"], "track")
        self.assertEqual(data["transfer_mode"], "cues-only")

    def test_port_cli_accepts_collection_scope(self):
        with TemporaryDirectory() as tmpdir:
            exit_code = main(
                [
                    "port",
                    "rb-to-serato",
                    "--rekordbox-xml",
                    str(FIXTURE),
                    "--collection",
                    "--transfer-mode",
                    "match-only",
                    "--out",
                    tmpdir,
                ]
            )
            data = json.loads((Path(tmpdir) / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(data["scope"], "collection")
        self.assertEqual(data["summary"]["cue_intents"], 0)

    def test_port_cli_accepts_playlists_file_and_summary_only(self):
        with TemporaryDirectory() as tmpdir:
            playlist_file = Path(tmpdir) / "playlists.txt"
            playlist_file.write_text("ROOT / Fixture Playlist\n", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "port",
                        "rb-to-serato",
                        "--rekordbox-xml",
                        str(FIXTURE),
                        "--playlists-file",
                        str(playlist_file),
                        "--out",
                        tmpdir,
                        "--summary-only",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn("Dry-run Serato summary", stdout.getvalue())
        self.assertFalse((Path(tmpdir) / "port-manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
