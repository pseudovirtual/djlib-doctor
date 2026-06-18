import json
import math
import sqlite3
import struct
import wave
from pathlib import Path


def write_click_wav(path: Path) -> None:
    sample_rate = 44100
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = []
        for index in range(sample_rate * 2):
            value = 0
            if sample_rate <= index < sample_rate + 400:
                value = int(28000 * math.sin(2 * math.pi * 1000 * (index - sample_rate) / sample_rate))
            frames.append(struct.pack("<h", value))
        handle.writeframes(b"".join(frames))


def make_rekordbox_db(path: Path, audio: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE djmdContent(ID INTEGER PRIMARY KEY, FolderPath TEXT, FileNameL TEXT, Title TEXT);
            CREATE TABLE djmdCue(ID INTEGER PRIMARY KEY, ContentID INTEGER, InMsec INTEGER, OutMsec INTEGER);
            """
        )
        conn.execute(
            "INSERT INTO djmdContent(ID, FolderPath, FileNameL, Title) VALUES(1, ?, ?, 'Track One')",
            (str(audio.parent), audio.name),
        )
        conn.execute("INSERT INTO djmdCue(ID, ContentID, InMsec, OutMsec) VALUES(1, 1, 1000, 1500)")
        conn.commit()
    finally:
        conn.close()


def cue_row(path: Path) -> tuple[int, int]:
    conn = sqlite3.connect(path)
    try:
        return conn.execute("SELECT InMsec, OutMsec FROM djmdCue WHERE ID = 1").fetchone()
    finally:
        conn.close()


def write_operations(tmp: Path, source: Path, target: Path, dat: Path, ext: Path) -> Path:
    ops = tmp / "convert.json"
    ops.write_text(
        json.dumps(
            {
                "operations": [
                    {
                        "track_id": "1",
                        "source": str(source),
                        "target": str(target),
                        "preset": "aac-m4a-128",
                        "anlz_files": [str(dat), str(ext)],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return ops
