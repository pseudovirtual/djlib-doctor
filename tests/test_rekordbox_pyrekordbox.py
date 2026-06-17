import unittest
from pathlib import Path

from djlib_doctor.rekordbox_pyrekordbox import PyrekordboxUnavailable, open_master_database


class FakeMasterDatabase:
    calls = []

    def __init__(self, path=None, key="", unlock=True):
        self.calls.append({"path": path, "key": key, "unlock": unlock})


class RekordboxPyrekordboxTests(unittest.TestCase):
    def test_open_master_database_fails_closed_without_dependency(self):
        with self.assertRaisesRegex(PyrekordboxUnavailable, r"Rekordbox SQLCipher backend is unavailable"):
            open_master_database(Path("master.db"), importer=lambda: (_ for _ in ()).throw(ImportError("missing")))

    def test_open_master_database_reports_unsupported_or_locked_database(self):
        class LockedMasterDatabase:
            def __init__(self, path=None, key="", unlock=True):
                raise RuntimeError("file is encrypted or is not a database")

        with self.assertRaisesRegex(PyrekordboxUnavailable, r"could not unlock or read Rekordbox master.db"):
            open_master_database(Path("master.db"), importer=lambda: LockedMasterDatabase)

    def test_open_master_database_uses_pyrekordbox_master_database(self):
        FakeMasterDatabase.calls.clear()

        db = open_master_database(Path("master.db"), key="402fd-test", importer=lambda: FakeMasterDatabase)

        self.assertIsInstance(db, FakeMasterDatabase)
        self.assertEqual(FakeMasterDatabase.calls, [{"path": Path("master.db"), "key": "402fd-test", "unlock": True}])


if __name__ == "__main__":
    unittest.main()
