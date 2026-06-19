from __future__ import annotations

import os
import unittest
from pathlib import Path

from djlib_doctor.cues import CueKind, CueType
from djlib_doctor.rekordbox_db_read import _all, library_from_pyrekordbox_db
from djlib_doctor.rekordbox_pyrekordbox import close_master_database, open_master_database

REAL_REKORDBOX_DB_ENV = "DJLIB_DOCTOR_REAL_REKORDBOX_DB"


class RealRekordboxDbReadTests(unittest.TestCase):
    def test_configured_real_db_classifies_hotcues_and_loops(self):
        configured = os.environ.get(REAL_REKORDBOX_DB_ENV, "")
        if not configured:
            self.skipTest(f"Set {REAL_REKORDBOX_DB_ENV} to a local Rekordbox master.db copy")
        path = Path(configured).expanduser()
        if not path.exists():
            self.skipTest(f"{REAL_REKORDBOX_DB_ENV} path does not exist: {path}")
        try:
            db = open_master_database(path, unlock=True)
        except ImportError as exc:
            self.skipTest(f"pyrekordbox unavailable: {exc}")
        try:
            raw_cues = _all(db.get_cue())
            library = library_from_pyrekordbox_db(db)
        finally:
            close_master_database(db)

        parsed_cues = tuple(cue for track in library.tracks for cue in track.cues)
        raw_hotcues = sum(1 for cue in raw_cues if _raw_bool(cue, "is_hot_cue") or (_raw_int(cue, "Kind") or 0) >= 1)
        raw_loops = sum(1 for cue in raw_cues if (_raw_float(cue, "OutMsec") or 0) > 0)

        self.assertGreater(raw_hotcues, 0)
        self.assertEqual(sum(cue.kind is CueKind.HOTCUE for cue in parsed_cues), raw_hotcues)
        self.assertEqual(sum(cue.cue_type is CueType.LOOP for cue in parsed_cues), raw_loops)
        self.assertTrue(
            all(cue.end is not None and cue.end > cue.start for cue in parsed_cues if cue.cue_type is CueType.LOOP)
        )


def _raw_int(row: object, name: str) -> int | None:
    value = getattr(row, name, None)
    return None if value in (None, "") else int(value)


def _raw_float(row: object, name: str) -> float | None:
    value = getattr(row, name, None)
    return None if value in (None, "") else float(value)


def _raw_bool(row: object, name: str) -> bool:
    value = getattr(row, name, None)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


if __name__ == "__main__":
    unittest.main()
