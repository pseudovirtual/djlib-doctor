import contextlib
import csv
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.snapshot import create_snapshot

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class SnapshotTests(unittest.TestCase):
    def test_create_snapshot_writes_expected_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "snapshot"
            result = create_snapshot(FIXTURE, out_dir, check_files=False)

            self.assertTrue(result.snapshot_path.exists())
            self.assertTrue(result.verification_text_path.exists())
            self.assertTrue(result.verification_json_path.exists())
            self.assertTrue(result.missing_files_path.exists())
            self.assertTrue(result.streaming_placeholders_path.exists())
            self.assertTrue(result.track_summary_path.exists())
            self.assertTrue(result.cue_summary_path.exists())
            self.assertTrue(result.playlist_summary_path.exists())

            snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["schema_version"], "1.0")
            self.assertEqual(snapshot["command"]["name"], "snapshot")
            self.assertFalse(snapshot["command"]["options"]["redact_paths"])
            self.assertEqual(snapshot["verification"]["status"], "pass")

            with result.streaming_placeholders_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["track_id"], "3")

            with result.track_summary_path.open(encoding="utf-8") as handle:
                track_rows = list(csv.DictReader(handle))
            self.assertEqual(len(track_rows), 3)
            self.assertIn("playlist_count", track_rows[0])

            with result.cue_summary_path.open(encoding="utf-8") as handle:
                cue_rows = list(csv.DictReader(handle))
            self.assertEqual(len(cue_rows), 3)

            with result.playlist_summary_path.open(encoding="utf-8") as handle:
                playlist_rows = list(csv.DictReader(handle))
            self.assertEqual(playlist_rows[0]["playlist"], "ROOT / Fixture Playlist")

    def test_snapshot_with_music_root_writes_audio_inventory(self):
        with TemporaryDirectory() as tmpdir:
            music_root = Path(tmpdir) / "music"
            music_root.mkdir()
            (music_root / "track.aiff").write_bytes(b"fixture")
            (music_root / "notes.txt").write_text("not audio", encoding="utf-8")

            result = create_snapshot(FIXTURE, Path(tmpdir) / "snapshot", music_root=music_root, check_files=False)

            self.assertIsNotNone(result.filesystem_inventory_path)
            self.assertTrue(result.filesystem_inventory_path.exists())
            with result.filesystem_inventory_path.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["extension"], ".aiff")

    def test_redacted_snapshot_uses_portable_artifacts_without_raw_paths(self):
        with TemporaryDirectory() as tmpdir:
            music_root = Path(tmpdir) / "music"
            music_root.mkdir()
            (music_root / "track.aiff").write_bytes(b"fixture")

            result = create_snapshot(
                FIXTURE,
                Path(tmpdir) / "snapshot",
                music_root=music_root,
                check_files=True,
                redact_paths=True,
            )

            snapshot = json.loads(result.snapshot_path.read_text(encoding="utf-8"))
            self.assertTrue(snapshot["redacted"])
            self.assertTrue(snapshot["command"]["options"]["redact_paths"])
            self.assertTrue(snapshot["command"]["options"]["music_root_provided"])
            self.assertEqual(snapshot["artifacts"]["track_summary_csv"], "track-summary.csv")
            self.assertIn("<redacted>", snapshot["source"]["rekordbox_xml"])

            texts = [
                result.verification_text_path.read_text(encoding="utf-8"),
                result.verification_json_path.read_text(encoding="utf-8"),
                result.missing_files_path.read_text(encoding="utf-8"),
                result.track_summary_path.read_text(encoding="utf-8"),
                result.filesystem_inventory_path.read_text(encoding="utf-8")
                if result.filesystem_inventory_path
                else "",
            ]

        combined = "\n".join(texts)
        self.assertIn("<redacted>", combined)
        self.assertNotIn("/private/tmp/djlib-doctor-fixture", combined)
        self.assertNotIn(str(music_root), combined)

    def test_snapshot_cli_returns_success_for_passing_snapshot(self):
        with TemporaryDirectory() as tmpdir:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    ["snapshot", "--rekordbox-xml", str(FIXTURE), "--out", str(Path(tmpdir) / "run"), "--no-file-check"]
                )

            self.assertEqual(exit_code, 0)
            self.assertIn("Snapshot written:", stdout.getvalue())

    def test_snapshot_cli_supports_redacted_paths(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "run"
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(
                    [
                        "snapshot",
                        "--rekordbox-xml",
                        str(FIXTURE),
                        "--out",
                        str(out_dir),
                        "--no-file-check",
                        "--redact-paths",
                    ]
                )

            snapshot = json.loads((out_dir / "snapshot.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(snapshot["redacted"])
        self.assertIn("Snapshot written:", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
