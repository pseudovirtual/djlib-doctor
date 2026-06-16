from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest
import xml.etree.ElementTree as ET

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


def make_serato_root_with_ordered_marker_tracks(path: Path) -> None:
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
            VALUES
                (1, 'Music/Track One.aiff', 'Track One', 'Artist One'),
                (2, 'Music/Track Two.aiff', 'Track Two', 'Artist Two');
            """
        )
        marker_payloads = {
            1: (
                {"intent": "serato_hotcue", "slot": 0, "start_ms": 12345, "label": "Cue A"},
                {"intent": "serato_saved_loop", "slot": 1, "start_ms": 48000, "end_ms": 56000, "label": "Loop B"},
            ),
            2: (
                {"intent": "serato_hotcue", "slot": 2, "start_ms": 22222, "label": "Cue C"},
                {"intent": "serato_saved_loop", "slot": 3, "start_ms": 64000, "end_ms": 80000, "label": "Loop D"},
            ),
        }
        for asset_id, intents in marker_payloads.items():
            conn.execute("UPDATE asset SET markers2 = ? WHERE id = ?", (build_markers2_payload(intents), asset_id))
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

    def test_serato_to_rekordbox_preserves_marker_fidelity_and_playlist_order(self):
        with TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            library = tmp / "Library"
            library.mkdir()
            make_serato_root_with_ordered_marker_tracks(library / "root.sqlite")
            crate = tmp / "Ordered.crate"
            write_serato_crate(crate, ("Music/Track Two.aiff", "Music/Track One.aiff"))

            plan = build_serato_to_rekordbox_plan(library, crate, collection_root=Path("/Users/test"))
            outputs = write_serato_to_rekordbox_plan(plan, tmp / "out")
            manifest = json.loads(Path(outputs["manifest"]).read_text(encoding="utf-8"))
            xml_root = ET.fromstring(Path(outputs["rekordbox_xml_preview"]).read_text(encoding="utf-8"))

        self.assertEqual([track["portable_id"] for track in manifest["tracks"]], ["Music/Track Two.aiff", "Music/Track One.aiff"])
        self.assertEqual(
            _cue_summary(manifest["tracks"][0]),
            [
                ("hotcue", "cue", 2, 22222, None, "Cue C"),
                ("loop", "loop", 3, 64000, 80000, "Loop D"),
            ],
        )
        self.assertEqual(
            _cue_summary(manifest["tracks"][1]),
            [
                ("hotcue", "cue", 0, 12345, None, "Cue A"),
                ("loop", "loop", 1, 48000, 56000, "Loop B"),
            ],
        )
        self.assertEqual([node.attrib["Key"] for node in xml_root.findall("./PLAYLISTS/NODE/NODE/TRACK")], ["1", "2"])
        track_marks = {track.attrib["TrackID"]: track.findall("POSITION_MARK") for track in xml_root.findall("./COLLECTION/TRACK")}
        self.assertEqual(track_marks["1"][0].attrib, {"Type": "0", "Start": "22.222", "Num": "2", "Name": "Cue C"})
        self.assertEqual(track_marks["1"][1].attrib, {"Type": "4", "Start": "64.000", "Num": "3", "Name": "Loop D", "End": "80.000"})
        self.assertEqual(track_marks["2"][0].attrib, {"Type": "0", "Start": "12.345", "Num": "0", "Name": "Cue A"})
        self.assertEqual(track_marks["2"][1].attrib, {"Type": "4", "Start": "48.000", "Num": "1", "Name": "Loop B", "End": "56.000"})


def _cue_summary(track: dict[str, object]) -> list[tuple[object, ...]]:
    return [(cue["kind"], cue["cue_type"], cue["slot"], cue["start_ms"], cue["end_ms"], cue["label"]) for cue in track["cues"]]


if __name__ == "__main__":
    unittest.main()
