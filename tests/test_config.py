from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, load_config, write_config


class ConfigTests(unittest.TestCase):
    def test_write_and_load_config_round_trip(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "djlib-doctor.json"
            write_config(
                path,
                default_config(
                    rekordbox_xml=Path("/tmp/export.xml"),
                    serato_library_dir=Path("/tmp/serato-library"),
                    serato_music_dir=Path("/tmp/_Serato_"),
                ),
            )
            config = load_config(path)

        self.assertEqual(config["rekordbox_xml"], "/tmp/export.xml")
        self.assertEqual(config["serato_library_dir"], "/tmp/serato-library")
        self.assertEqual(config["crate_prefix"], "RB - ")

    def test_load_config_rejects_unknown_keys(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text(json.dumps({"surprise": True}), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(path)

    def test_config_cli_init_and_show(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "config.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["config", "init", "--out", str(path), "--crate-prefix", "SERATO - "]), 0)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["config", "show", "--config", str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
