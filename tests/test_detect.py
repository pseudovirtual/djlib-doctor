from pathlib import Path
from tempfile import TemporaryDirectory
import contextlib
import io
import json
import unittest

from djlib_doctor.cli import main
from djlib_doctor.detect import detect_libraries


class DetectTests(unittest.TestCase):
    def test_detect_libraries_finds_synthetic_rekordbox_and_serato_paths(self):
        with TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            volume = Path(tmpdir) / "External"
            (home / "Library" / "Pioneer" / "rekordbox").mkdir(parents=True)
            (home / "Library" / "Pioneer" / "rekordbox" / "master.db").write_bytes(b"sqlite")
            (home / "Desktop").mkdir()
            (home / "Desktop" / "rekordbox.xml").write_text("<DJ_PLAYLISTS />", encoding="utf-8")
            serato = volume / "_Serato_"
            (serato / "Subcrates").mkdir(parents=True)
            (serato / "database V2").write_bytes(b"serato")
            (serato / "root.sqlite").write_bytes(b"sqlite")

            report = detect_libraries(home, (volume,))

        found = {(item["platform"], item["kind"]) for item in report["findings"]}
        self.assertIn(("rekordbox", "master_db"), found)
        self.assertIn(("rekordbox", "xml_export"), found)
        self.assertIn(("serato", "music_dir"), found)
        self.assertIn(("serato", "database_v2"), found)
        self.assertIn(("serato", "subcrates"), found)
        self.assertIn(("serato", "root_sqlite"), found)
        self.assertEqual(report["summary"]["rekordbox"], 2)
        self.assertEqual(report["summary"]["serato"], 4)

    def test_detect_cli_prints_json(self):
        with TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            (home / "Music" / "_Serato_").mkdir(parents=True)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["detect", "--home", str(home), "--json"]), 0)

        report = json.loads(stdout.getvalue())
        self.assertEqual(report["findings"][0]["kind"], "music_dir")


if __name__ == "__main__":
    unittest.main()
