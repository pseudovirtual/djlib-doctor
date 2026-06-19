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

    def test_api_examples_are_documented(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        doc = ROOT / "docs" / "api-examples.md"
        text = doc.read_text(encoding="utf-8")

        self.assertIn("api-examples.md", index)
        self.assertIn("parse_rekordbox_xml", text)
        self.assertIn("verify_library", text)
        self.assertIn("build_missing_files_plan", text)

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

    def test_rekordbox_db_schema_documents_real_cue_columns(self):
        text = (ROOT / "docs" / "rekordbox-db-schema.md").read_text(encoding="utf-8")
        for phrase in ("is_hot_cue", "is_memory_cue", "Kind - 1", "OutMsec > 0"):
            self.assertIn(phrase, text)
        self.assertNotIn("`Type` carries cue-vs-loop", text)
        self.assertNotIn("`HotCue`/`Kind` distinguish", text)

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

    def test_roadmap_records_real_validation_and_release_blockers(self):
        backlog = (ROOT / "docs" / "roadmap" / "BACKLOG.md").read_text(encoding="utf-8")
        state = (ROOT / "docs" / "roadmap" / "STATE.md").read_text(encoding="utf-8")

        for phrase in (
            "PCOB/PCO2 len_cues count offset",
            "cue-shift SIGN/necessity",
            "Serato Markers2/BeatGrid",
            "sqlcipher3-wheels coverage gap",
        ):
            self.assertIn(phrase, backlog)
        for phrase in (
            "real encrypted Rekordbox master.db",
            "real `.DAT` and `.EXT` ANLZ files",
            "real Rekordbox import/export check",
            "real Serato Markers2 and BeatGrid capture",
        ):
            self.assertIn(phrase, state)

    def test_phase_i_rekordbox_728_shift_result_is_documented(self):
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        state = (ROOT / "docs" / "roadmap" / "STATE.md").read_text(encoding="utf-8")
        result = (ROOT / "docs" / "phase-i-results.md").read_text(encoding="utf-8")

        self.assertIn("phase-i-results.md", index)
        self.assertIn("Rekordbox 7.2.8", state)
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

    def test_phase_i_real_data_followups_are_recorded(self):
        backlog = (ROOT / "docs" / "roadmap" / "BACKLOG.md").read_text(encoding="utf-8")
        state = (ROOT / "docs" / "roadmap" / "STATE.md").read_text(encoding="utf-8")

        for phrase in (
            "I5: Fix Serato `database V2` track extraction",
            "I6: Document local Rekordbox ANLZ scope",
            "I7: Add an opt-in, local-only real Serato Markers2 validation harness",
        ):
            self.assertIn(phrase, backlog)
        for phrase in (
            "Serato `database V2` nested `otrk` extraction",
            "local ANLZ cue-scope documentation",
            "opt-in local Markers2 validation harness",
            "PCOB/PCO2 cue-count offsets",
        ):
            self.assertIn(phrase, state)

    def test_local_anlz_cue_scope_is_documented(self):
        docs = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("docs/phase-i-results.md", "docs/how-to-convert-without-losing-cues.md")
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
