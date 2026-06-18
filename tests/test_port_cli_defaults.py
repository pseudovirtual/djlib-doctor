import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.helpers import insert_serato_asset, make_serato_root

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, write_config

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class PortCliDefaultsTests(unittest.TestCase):
    def test_rb_to_serato_port_uses_configured_xml_without_using_primary_direction(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            config = tmp / "config.json"
            write_config(config, default_config(primary="serato", rekordbox_xml=FIXTURE))

            exit_code = main(
                ["port", "rb-to-serato", "--config", str(config), "--collection", "--out", str(tmp / "out")]
            )
            manifest = json.loads((tmp / "out" / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["source_platform"], "rekordbox_xml")
        self.assertEqual(manifest["target_platform"], "serato")

    def test_serato_to_rb_port_uses_configured_paths_without_using_primary_direction(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "_Serato_"
            library.mkdir()
            make_serato_root(library / "root.sqlite")
            insert_serato_asset(library / "root.sqlite", "Music/Track One.aiff")
            config = tmp / "config.json"
            write_config(config, default_config(primary="rekordbox", serato_library_dir=library, music_root=tmp))

            exit_code = main(
                ["port", "serato-to-rb", "--config", str(config), "--collection", "--out", str(tmp / "out")]
            )
            manifest = json.loads((tmp / "out" / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["source_platform"], "serato")
        self.assertEqual(manifest["target_platform"], "rekordbox_xml")

    def test_rb_to_serato_port_detects_rekordbox_xml_when_config_and_flag_are_omitted(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home = tmp / "home"
            desktop = home / "Desktop"
            desktop.mkdir(parents=True)
            detected_xml = desktop / "rekordbox.xml"
            detected_xml.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")

            exit_code = main(["port", "rb-to-serato", "--home", str(home), "--collection", "--out", str(tmp / "out")])
            manifest = json.loads((tmp / "out" / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["source_platform"], "rekordbox_xml")

    def test_serato_to_rb_port_detects_serato_paths_when_config_and_flags_are_omitted(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home = tmp / "home"
            library = home / "Music" / "_Serato_"
            library.mkdir(parents=True)
            make_serato_root(library / "root.sqlite")
            insert_serato_asset(library / "root.sqlite", "Track One.aiff")

            exit_code = main(["port", "serato-to-rb", "--home", str(home), "--collection", "--out", str(tmp / "out")])
            manifest = json.loads((tmp / "out" / "port-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["source_platform"], "serato")
        self.assertEqual(manifest["summary"]["tracks"], 1)


if __name__ == "__main__":
    unittest.main()
