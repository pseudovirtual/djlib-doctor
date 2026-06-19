from __future__ import annotations

import contextlib
import sqlite3
import sys
import types
from pathlib import Path
from unittest import mock


def make_serato_root(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE serato(revision INT DEFAULT 0);
            INSERT INTO serato(revision) VALUES(10);
            CREATE TABLE asset(id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL, portable_id TEXT NOT NULL DEFAULT '', file_name TEXT, file_size INTEGER, type TEXT DEFAULT '', format TEXT DEFAULT '', artist TEXT DEFAULT '', comments TEXT DEFAULT '', name TEXT DEFAULT '', album TEXT DEFAULT '', genre TEXT DEFAULT '', key TEXT DEFAULT '', bpm REAL, length_ms INTEGER, time_added INTEGER DEFAULT 0, time_modified INTEGER DEFAULT 0, analysis_flags INTEGER DEFAULT 0, architectures INTEGER DEFAULT 0);
            CREATE UNIQUE INDEX asset__unique_portable_id ON asset(portable_id COLLATE NOCASE);
            CREATE TABLE space_asset(id INTEGER PRIMARY KEY, asset_id INTEGER NOT NULL, space_id INTEGER NOT NULL, UNIQUE(asset_id, space_id));
            CREATE TABLE container(id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL, parent_id INTEGER, name TEXT NOT NULL, type INTEGER DEFAULT 1, list_order INTEGER NOT NULL, space_id INTEGER DEFAULT NULL, time_added INTEGER DEFAULT 0, expanded INTEGER DEFAULT 0, portable_id TEXT DEFAULT '', UNIQUE(parent_id, name COLLATE NOCASE, type));
            INSERT INTO container(id, revision, parent_id, name, type, list_order, space_id, time_added, portable_id)
            VALUES(3, 10, 0, 'Serato Library root', 0, 1, 2, 1, '');
            CREATE TABLE container_asset(id INTEGER PRIMARY KEY AUTOINCREMENT, revision INTEGER NOT NULL, container_id INTEGER NOT NULL, space_asset_id INTEGER NOT NULL, list_order INTEGER, time_added INTEGER DEFAULT 0);
            """
        )
        conn.commit()
    finally:
        conn.close()


def insert_serato_asset(root_sqlite: Path, portable_id: str) -> None:
    conn = sqlite3.connect(root_sqlite)
    try:
        conn.execute(
            "INSERT INTO asset(revision, portable_id, file_name, name, artist) VALUES(?, ?, ?, ?, ?)",
            (1, portable_id, Path(portable_id).name, Path(portable_id).stem, "Artist One"),
        )
        conn.commit()
    finally:
        conn.close()


def make_rekordbox_import_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE djmdContent(
                ID INTEGER PRIMARY KEY,
                FolderPath TEXT,
                FileNameL TEXT,
                Title TEXT,
                ArtistName TEXT
            );
            CREATE TABLE djmdCue(
                -- Real Rekordbox 7 cue rows use InMsec/OutMsec, Kind, and
                -- is_hot_cue/is_memory_cue; there is no HotCue column.
                ID INTEGER PRIMARY KEY,
                ContentID INTEGER,
                InMsec INTEGER,
                OutMsec INTEGER,
                Kind INTEGER,
                is_hot_cue INTEGER,
                is_memory_cue INTEGER,
                Name TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


class _FakeTags(dict):
    def setall(self, key, values):
        self[key] = values


class _FakeAudio:
    def __init__(self, path):
        self.path = path
        self.tags = _FakeTags()

    def add_tags(self):
        self.tags = _FakeTags()

    def save(self):
        pass


class _FakeGEOB:
    def __init__(self, **kwargs):
        self.data = kwargs["data"]


class _FakeMP4FreeForm(bytes):
    def __new__(cls, data, dataformat=None):
        return bytes.__new__(cls, data)


@contextlib.contextmanager
def fake_mutagen():
    written = []

    def audio_factory(path):
        return _FakeAudio(path)

    def geob_factory(**kwargs):
        frame = _FakeGEOB(**kwargs)
        written.append(frame.data)
        return frame

    def freeform_factory(data, dataformat=None):
        written.append(bytes(data))
        return _FakeMP4FreeForm(data, dataformat=dataformat)

    aiff = types.ModuleType("mutagen.aiff")
    aiff.AIFF = audio_factory
    mp3 = types.ModuleType("mutagen.mp3")
    mp3.MP3 = audio_factory
    mp4 = types.ModuleType("mutagen.mp4")
    mp4.MP4 = audio_factory
    mp4.MP4FreeForm = freeform_factory
    mp4.AtomDataType = types.SimpleNamespace(IMPLICIT=0)
    id3 = types.ModuleType("mutagen.id3")
    id3.GEOB = geob_factory
    for name in ("TALB", "TBPM", "TCON", "TIT2", "TKEY", "TPE1"):
        setattr(id3, name, lambda **kwargs: kwargs)
    with mock.patch.dict(
        sys.modules,
        {"mutagen.aiff": aiff, "mutagen.id3": id3, "mutagen.mp3": mp3, "mutagen.mp4": mp4},
    ):
        yield written
