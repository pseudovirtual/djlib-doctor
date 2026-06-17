import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT_DOCS = (
    ".agents/skills/djlib-doctor/SKILL.md",
    "plugins/djlib-doctor/skills/djlib-doctor/SKILL.md",
    "CLAUDE.md",
    "llms.txt",
    "llms-full.txt",
)
STALE_PHRASES = (
    "high-level import wrapper is still missing",
    "no DB writer exists",
    "future write workflow",
    "future DB-write guardrails",
)


class AgentDocsTests(unittest.TestCase):
    def test_agent_surfaces_include_rekordbox_db_import(self):
        for relative in AGENT_DOCS:
            with self.subTest(relative=relative):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("stage rekordbox-db-import", text)
                self.assertIn("install rekordbox-db", text)

    def test_agent_surfaces_do_not_contain_stale_write_guidance(self):
        combined = "\n".join((ROOT / relative).read_text(encoding="utf-8") for relative in AGENT_DOCS)
        for phrase in STALE_PHRASES:
            self.assertNotIn(phrase, combined)


if __name__ == "__main__":
    unittest.main()
