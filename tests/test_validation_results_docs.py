import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidationResultsDocsTests(unittest.TestCase):
    def test_live_validation_counts_are_recorded(self):
        docs = (ROOT / "docs" / "validation-results.md").read_text(encoding="utf-8")

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

    def test_fixture_hardening_results_are_recorded(self):
        result = (ROOT / "docs" / "validation-results.md").read_text(encoding="utf-8")

        for phrase in (
            "J4 fixture-hardening verification",
            "254 tests",
            "copy only `master.db`",
            "convert, move, and Serato-to-Rekordbox import",
            "plain-SQLite rejection assertions",
            "SQLCipher backend is installed",
        ):
            self.assertIn(phrase, result)


if __name__ == "__main__":
    unittest.main()
