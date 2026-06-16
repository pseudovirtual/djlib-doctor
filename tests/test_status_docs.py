from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StatusDocsTests(unittest.TestCase):
    def test_status_docs_do_not_claim_completed_work_is_missing(self):
        text = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("docs/end-to-end-product-plan.md", "docs/product-architecture.md", "SECURITY.md", "CHANGELOG.md")
        )

        self.assertNotIn("[ ] High-level Serato-to-Rekordbox staged `master.db` import wrapper", text)
        self.assertNotIn("The current code is read-only with respect to Rekordbox databases and music libraries.", text)
        self.assertNotIn("The next major gap is the Serato-to-Rekordbox staged DB import wrapper", text)


if __name__ == "__main__":
    unittest.main()
