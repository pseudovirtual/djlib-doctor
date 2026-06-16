from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest

from djlib_doctor.port_serato_rekordbox import build_serato_to_rekordbox_plan, write_serato_to_rekordbox_plan
from djlib_doctor.serato_crate import write_serato_crate
from djlib_doctor.serato_markers import build_markers2_payload


def make_serato_root_with_markers(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE asset(
                id INTEGER PRIMARY KEY,
                portable_id TEXT,
                name TEXT,
                artist TEXT,
                markers2 BLOB
            );
            INSERT INTO asset(id, portable_id, name, artist)
            VALUES(1, 'Music/Track One.aiff', 'Track One', 'Artist One');
            """
        )
        payload = build_markers2_payload(
            (
                {"intent": "serato_hotcue", "slot": 0, "start_ms": 12345, "label": "Cue A"},
                {"intent": "serato_saved_loop", "slot": 1, "start_ms": 48000, "end_ms": 56000, "label": "Loop B"},
            )
        )
        conn.execute("UPDATE asset SET markers2 = ? WHERE id = 1", (payload,))
        conn.commit()
    finally:
        conn.close()


class PortSeratoRekordboxCueTests(unittest.TestCase):
    def test_serato_to_rekordbox_plan_reads_marker_cues(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root_with_markers(library / "root.sqlite")
            crate = tmp / "Test.crate"
            write_serato_crate(crate, ("Music/Track One.aiff",))

            plan = build_serato_to_rekordbox_plan(library, crate, collection_root=Path("/Users/test"))
            outputs = write_serato_to_rekordbox_plan(plan, tmp / "out")
            manifest = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
            xml = Path(outputs["rekordbox_xml_preview"]).read_text(encoding="utf-8")

        cues = manifest["tracks"][0]["cues"]
        self.assertEqual(len(cues), 2)
        self.assertEqual(cues[0]["label"], "Cue A")
        self.assertEqual(cues[1]["cue_type"], "loop")
        self.assertIn("POSITION_MARK", xml)
        self.assertIn('Name="Loop B"', xml)


if __name__ == "__main__":
    unittest.main()
