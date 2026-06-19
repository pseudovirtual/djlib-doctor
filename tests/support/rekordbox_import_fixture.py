from __future__ import annotations

import sqlite3
from pathlib import Path

from djlib_doctor.io_utils import write_json


def make_serato_to_rekordbox_manifest(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": "1.0",
            "mode": "dry_run_only",
            "source_platform": "serato",
            "target_platform": "rekordbox_xml",
            "transfer_mode": "full",
            "tracks": [_track()],
            "skipped": [],
        },
    )


def make_unsupported_rekordbox_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE something_else(id INTEGER PRIMARY KEY)")
        conn.commit()
    finally:
        conn.close()


def make_serato_root(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE asset(portable_id TEXT, name TEXT, artist TEXT)")
        conn.execute("INSERT INTO asset VALUES('Music/Track One.aiff', 'Track One', 'Artist One')")
        conn.commit()
    finally:
        conn.close()


def _track() -> dict[str, object]:
    return {
        "track_id": "1",
        "portable_id": "Music/Track One.aiff",
        "path": "/Music/Track One.aiff",
        "title": "Track One",
        "artist": "Artist One",
        "album": "Album",
        "genre": "House",
        "key": "8A",
        "bpm": 124.0,
        "length_ms": 300000,
        "cues": [
            {"kind": "hotcue", "cue_type": "cue", "start_ms": 12345, "end_ms": None, "slot": 0, "label": "Cue A"},
            {"kind": "hotcue", "cue_type": "loop", "start_ms": 48000, "end_ms": 56000, "slot": 1, "label": "Loop B"},
        ],
    }
