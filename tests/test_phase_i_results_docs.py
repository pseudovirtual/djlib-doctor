import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PhaseIResultsDocsTests(unittest.TestCase):
    def test_live_validation_counts_are_recorded(self):
        result = (ROOT / "docs" / "phase-i-results.md").read_text(encoding="utf-8")
        state = (ROOT / "docs" / "roadmap" / "STATE.md").read_text(encoding="utf-8")
        docs = f"{result}\n{state}"

        for phrase in (
            "150 real .DAT",
            "2160 .EXT",
            "0 mismatches",
            "30/30 real crates",
            "1550 track refs",
            "704/704 real otrk",
            "pfil/tsng/tart/talb/tgen/tkey",
            "1086 hotcues",
            "29 loops",
            "~40 memory",
            "hotcue slot = Kind - 1",
        ):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
