from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.port_serato import build_rekordbox_to_serato_plan, write_rekordbox_to_serato_plan
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
        self.assertIn("serato_hotcue", intents)
        self.assertIn("serato_saved_loop", intents)
        self.assertEqual(plan.skipped[0]["reason"], "not_local_file")

    def test_write_rekordbox_to_serato_plan_writes_manifest_and_crate_preview(self):
        with TemporaryDirectory() as tmpdir:
            plan = build_rekordbox_to_serato_plan(FIXTURE, "ROOT / Fixture Playlist")
            outputs = write_rekordbox_to_serato_plan(plan, Path(tmpdir))
            manifest = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
            crate = read_serato_crate(Path(outputs["crate_preview"]))

        self.assertEqual(manifest["mode"], "dry_run_only")
        self.assertEqual(manifest["summary"]["tracks"], 1)
        self.assertEqual(len(crate.tracks), 1)

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


if __name__ == "__main__":
    unittest.main()
