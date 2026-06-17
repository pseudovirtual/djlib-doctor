import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_FIXTURES = ROOT / "tests" / "fixtures" / "real"
CAPTURE_DOC = ROOT / "docs" / "real-fixtures.md"


class RealFixtureLayoutTests(unittest.TestCase):
    def test_capture_procedure_and_layout_are_documented(self):
        self.assertTrue(CAPTURE_DOC.exists())
        text = CAPTURE_DOC.read_text(encoding="utf-8")
        for phrase in (
            "Serato GEOB tags",
            "database V2",
            "decrypted master.db",
            "matching XML export",
            "Do not commit private library data",
        ):
            self.assertIn(phrase, text)

        self.assertTrue((REAL_FIXTURES / "README.md").exists())
        self.assertTrue((REAL_FIXTURES / ".gitignore").exists())

    def test_optional_real_fixture_manifest_skips_when_absent(self):
        manifest = REAL_FIXTURES / "manifest.json"
        if not manifest.exists():
            self.skipTest("no contributor-supplied real fixture manifest")

        data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], "1.0")
        self.assertIn("fixtures", data)


if __name__ == "__main__":
    unittest.main()
