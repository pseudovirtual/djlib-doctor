from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, write_config
from djlib_doctor.sync_planner import plan_sync
from tests.helpers import insert_serato_asset, make_serato_root


FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class SyncPlannerTests(unittest.TestCase):
    def test_plans_rekordbox_primary_to_serato(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config = default_config(primary="rekordbox", rekordbox_xml=FIXTURE)

            result = plan_sync(config, tmp / "sync", collection=True)
            manifest = json.loads(result.port_manifest.read_text(encoding="utf-8"))

        self.assertEqual(result.direction, "rb-to-serato")
        self.assertEqual(manifest["source_platform"], "rekordbox_xml")
        self.assertEqual(manifest["target_platform"], "serato")
        self.assertTrue(result.certification.passed)

    def test_plans_serato_primary_to_rekordbox(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            insert_serato_asset(library / "root.sqlite", "Music/Track One.aiff")
            config = default_config(primary="serato", serato_library_dir=library, music_root=tmp)

            result = plan_sync(config, tmp / "sync", collection=True)
            manifest = json.loads(result.port_manifest.read_text(encoding="utf-8"))

        self.assertEqual(result.direction, "serato-to-rb")
        self.assertEqual(manifest["source_platform"], "serato")
        self.assertEqual(manifest["target_platform"], "rekordbox_xml")
        self.assertTrue(result.certification.passed)

    def test_sync_plan_cli_uses_primary_direction(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config_path = tmp / "config.json"
            write_config(config_path, default_config(primary="rekordbox", rekordbox_xml=FIXTURE))
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["sync", "plan", "--config", str(config_path), "--collection", "--out", str(tmp / "sync")])

            manifest = json.loads((tmp / "sync" / "port" / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertIn("Direction: rb-to-serato", stdout.getvalue())
        self.assertEqual(manifest["target_platform"], "serato")


if __name__ == "__main__":
    unittest.main()
