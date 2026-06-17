import contextlib
import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.helpers import make_serato_root

from djlib_doctor.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "rekordbox" / "simple.xml"


class DoctorTests(unittest.TestCase):
    def test_doctor_detects_and_checks_rekordbox_and_serato(self):
        with TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            desktop = home / "Desktop"
            serato = home / "Music" / "_Serato_"
            desktop.mkdir(parents=True)
            serato.mkdir(parents=True)
            (desktop / "rekordbox.xml").write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
            make_serato_root(serato / "root.sqlite")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(home)])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Rekordbox XML: PASS", output)
        self.assertIn("Serato root.sqlite: PASS", output)
        self.assertIn("Punch list:", output)
        self.assertIn("djlib-doctor snapshot --rekordbox-xml", output)
        self.assertIn("djlib-doctor inspect serato --library-dir", output)

    def test_doctor_prints_detect_command_when_nothing_found(self):
        with TemporaryDirectory() as tmpdir:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = main(["doctor", "--home", str(Path(tmpdir) / "home")])

        self.assertEqual(exit_code, 0)
        self.assertIn("No Rekordbox or Serato libraries found", stdout.getvalue())
        self.assertIn("djlib-doctor detect", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
