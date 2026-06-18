import unittest
from pathlib import Path

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
        self.assertIn("encrypted `master.db` reads and staged writes are generated-fixture tested", readme)
        self.assertIn("real captured DB certification is still pending", readme)

    def test_how_to_docs_are_linked_from_readme_and_docs_index(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        required = {
            "how-to-convert-without-losing-cues.md": (
                "rekordbox-convert",
                "--cue-shift auto",
                "INSTALL_REKORDBOX_CONVERT",
            ),
            "how-to-port-one-crate.md": ("port serato-to-rb", "certify serato-to-rb", "stage rekordbox-db-import"),
        }

        self.assertIn("Why Cue-Safe Migration Is Hard", readme)
        for filename, phrases in required.items():
            self.assertIn(filename, readme)
            self.assertIn(filename, index)
            text = (ROOT / "docs" / filename).read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase, text)

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

    def test_roadmap_tracks_active_backlog_and_state(self):
        backlog = ROOT / "docs" / "roadmap" / "BACKLOG.md"
        state = ROOT / "docs" / "roadmap" / "STATE.md"

        self.assertTrue(backlog.exists())
        self.assertTrue(state.exists())

        backlog_text = backlog.read_text(encoding="utf-8")
        state_text = state.read_text(encoding="utf-8")
        for label in ("Phase A", "A1", "Phase B", "B1", "Phase C", "C1", "Phase D", "D1"):
            self.assertIn(label, backlog_text)
        self.assertIn("Primary-library foundation", state_text)
        self.assertIn("Next", state_text)


if __name__ == "__main__":
    unittest.main()
