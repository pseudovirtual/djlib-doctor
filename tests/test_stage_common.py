import unittest
from pathlib import Path

from djlib_doctor.stage_common import backup_name


class StageCommonTests(unittest.TestCase):
    def test_backup_name_never_returns_an_absolute_path(self):
        name = backup_name(Path("/tmp/master.db"))

        self.assertFalse(Path(name).is_absolute())
        self.assertEqual(Path("/stage/backups") / name, Path("/stage/backups/tmp__master.db"))


if __name__ == "__main__":
    unittest.main()
