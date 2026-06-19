import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class SqlcipherPlatformDocsTests(unittest.TestCase):
    def test_sqlcipher_platform_caveat_is_documented(self):
        docs = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in ("README.md", "docs/rekordbox-db-schema.md", "docs/roadmap/STATE.md")
        )

        for phrase in (
            "sqlcipher3-wheels",
            "Intel/x86_64 macOS",
            "Python 3.13",
            "Apple Silicon",
            "Python <=3.12",
            "pip install",
        ):
            self.assertIn(phrase, docs)


if __name__ == "__main__":
    unittest.main()
