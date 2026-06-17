from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DocsStructureTests(unittest.TestCase):
    def test_docs_index_separates_current_and_archived_docs(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")

        self.assertIn("Current Docs", index)
        self.assertIn("Archived Docs", index)
        self.assertIn("feature-list.md", index)
        self.assertIn("archive/github-launch-plan.md", index)
        self.assertIn("archive/private-release-checklist.md", index)

    def test_launch_checklists_are_archived(self):
        self.assertFalse((ROOT / "docs" / "github-launch-plan.md").exists())
        self.assertFalse((ROOT / "docs" / "private-release-checklist.md").exists())
        self.assertTrue((ROOT / "docs" / "archive" / "github-launch-plan.md").exists())
        self.assertTrue((ROOT / "docs" / "archive" / "private-release-checklist.md").exists())

    def test_readme_separates_available_and_limited_coverage_claims(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        available = readme.split("## Safety Model", 1)[0]

        self.assertIn("## Experimental / Limited Coverage", readme)
        self.assertNotIn("fixture-backed", available)
        self.assertNotIn("Serato audio tags", available)
        self.assertIn("No real Rekordbox DB version is certified yet", readme)

    def test_port_workflow_modules_are_consolidated(self):
        src = ROOT / "src" / "djlib_doctor"
        leftovers = sorted(src.glob("port_rekordbox_serato_*.py")) + sorted(src.glob("port_serato_rekordbox_*.py"))

        self.assertEqual(leftovers, [])

    def test_rekordbox_db_schema_reference_documents_target_tables(self):
        doc = ROOT / "docs" / "rekordbox-db-schema.md"
        self.assertTrue(doc.exists())
        text = doc.read_text(encoding="utf-8")
        for phrase in ("pyrekordbox", "djmdContent", "djmdCue", "StatsFull", "rb_local_usn", "UUID"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
