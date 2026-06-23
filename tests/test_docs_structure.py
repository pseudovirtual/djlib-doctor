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
        self.assertIn("## What's Validated", readme)
        self.assertIn("Rekordbox encrypted `master.db` reads through pyrekordbox/SQLCipher", readme)
        self.assertIn("Serato saved-loop display is not yet verified", readme)
        self.assertIn("Broad Rekordbox and Serato version coverage", readme)

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

    def test_api_examples_are_documented(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        doc = ROOT / "docs" / "api-examples.md"
        text = doc.read_text(encoding="utf-8")

        self.assertIn("api-examples.md", index)
        self.assertIn("parse_rekordbox_xml", text)
        self.assertIn("verify_library", text)
        self.assertIn("build_missing_files_plan", text)

    def test_rekordbox_to_serato_modules_are_split_by_responsibility(self):
        src = ROOT / "src" / "djlib_doctor"
        expected = {
            "port_rekordbox_serato.py",
            "port_rekordbox_serato_cues.py",
            "port_rekordbox_serato_models.py",
            "port_rekordbox_serato_output.py",
            "port_rekordbox_serato_planning.py",
            "port_rekordbox_serato_policy.py",
            "port_rekordbox_serato_verify.py",
        }

        modules = {path.name for path in src.glob("port_rekordbox_serato*.py")}
        self.assertEqual(modules, expected)
        for module in expected:
            self.assertLessEqual(len((src / module).read_text(encoding="utf-8").splitlines()), 200)

    def test_rekordbox_db_schema_reference_documents_target_tables(self):
        doc = ROOT / "docs" / "rekordbox-db-schema.md"
        self.assertTrue(doc.exists())
        text = doc.read_text(encoding="utf-8")
        for phrase in ("pyrekordbox", "djmdContent", "djmdCue", "StatsFull", "rb_local_usn", "UUID"):
            self.assertIn(phrase, text)

    def test_rekordbox_db_schema_documents_real_cue_columns(self):
        text = (ROOT / "docs" / "rekordbox-db-schema.md").read_text(encoding="utf-8")
        for phrase in ("is_hot_cue", "is_memory_cue", "Kind - 1", "OutMsec > 0"):
            self.assertIn(phrase, text)
        self.assertNotIn("`Type` carries cue-vs-loop", text)
        self.assertNotIn("`HotCue`/`Kind` distinguish", text)

    def test_phase_i_rekordbox_728_shift_result_is_documented(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        result = (ROOT / "docs" / "validation-results.md").read_text(encoding="utf-8")

        self.assertIn("validation-results.md", index)
        for phrase in (
            "Rekordbox >=7 ignores AAC gapless",
            "cue/beat shift is positive",
            "MP3-to-M4A",
            "+21 ms",
            "WAV-to-M4A",
            "~23 ms",
            "--cue-shift auto",
        ):
            self.assertIn(phrase, result)

    def test_local_anlz_cue_scope_is_documented(self):
        docs = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("docs/validation-results.md", "docs/how-to-convert-without-losing-cues.md")
        )

        for phrase in (
            "local Rekordbox ANLZ files contain empty cue lists",
            "local user cues live in `master.db`",
            "ANLZ cue-tag shifting applies only to exported device media",
            "ANLZ beatgrids",
        ):
            self.assertIn(phrase, docs)

    def test_serato_database_v2_real_field_tags_are_documented(self):
        docs = (ROOT / "docs" / "serato-porting.md").read_text(encoding="utf-8")

        for phrase in ("pfil", "tsng", "tart", "tbpm", "ptrk", "pnam", "part"):
            self.assertIn(phrase, docs)

    def test_testing_fixture_rules_are_documented(self):
        doc = ROOT / "docs" / "testing-fixtures.md"
        text = doc.read_text(encoding="utf-8")

        for phrase in (
            "must mirror real bytes, columns, encryption, and tag structure",
            "pfil/tsng/tart/talb/tgen/tkey/tbpm",
            "Kind - 1",
            "is_hot_cue",
            "local ANLZ",
            "DJLIB_DOCTOR_REAL_SERATO",
            "DJLIB_DOCTOR_REAL_REKORDBOX_DB",
            "copy only `master.db`",
        ):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
