import contextlib
import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from djlib_doctor.cli import main
from djlib_doctor.config import default_config, load_config, write_config


class ConfigTests(unittest.TestCase):
    def test_write_and_load_config_round_trip(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "djlib-doctor.json"
            write_config(
                path,
                default_config(
                    primary="serato",
                    rekordbox_xml=Path("/tmp/export.xml"),
                    rekordbox_db=Path("/tmp/master.db"),
                    serato_library_dir=Path("/tmp/serato-library"),
                    serato_music_dir=Path("/tmp/_Serato_"),
                ),
            )
            config = load_config(path)

        self.assertEqual(config["primary"], "serato")
        self.assertEqual(config["rekordbox_xml"], "/tmp/export.xml")
        self.assertEqual(config["rekordbox_db"], "/tmp/master.db")
        self.assertEqual(config["serato_library_dir"], "/tmp/serato-library")
        self.assertEqual(config["crate_prefix"], "RB - ")

    def test_default_config_uses_rekordbox_primary(self):
        self.assertEqual(default_config()["primary"], "rekordbox")

    def test_load_config_rejects_invalid_primary(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.json"
            path.write_text(json.dumps({"primary": "engine"}), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(path)

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
                self.assertEqual(
                    main(
                        [
                            "config",
                            "init",
                            "--out",
                            str(path),
                            "--primary",
                            "serato",
                            "--rekordbox-db",
                            "/tmp/master.db",
                            "--crate-prefix",
                            "SERATO - ",
                        ]
                    ),
                    0,
                )
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["config", "show", "--config", str(path)]), 0)
            shown = json.loads(stdout.getvalue())

        self.assertEqual(shown["primary"], "serato")
        self.assertEqual(shown["rekordbox_db"], "/tmp/master.db")


if __name__ == "__main__":
    unittest.main()
