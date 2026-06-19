from __future__ import annotations

import sqlite3
import unittest
from pathlib import Path


def build_plain_rekordbox_fixture_db(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    _create_pyrekordbox_schema(path)
    conn = sqlite3.connect(path)
    try:
        populate_rekordbox_fixture_db(conn)
        conn.commit()
    finally:
        conn.close()
    return path


def _create_pyrekordbox_schema(path: Path) -> None:
    try:
        from pyrekordbox.db6.tables import Base
        from sqlalchemy import create_engine
    except ImportError:
        raise unittest.SkipTest("pyrekordbox is required to build Rekordbox DB fixtures") from None
    engine = create_engine(f"sqlite+pysqlite:///{path}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    conn = sqlite3.connect(path)
    try:
        _ensure_columns(conn, "djmdCue", {"is_hot_cue": "INTEGER", "is_memory_cue": "INTEGER", "Name": "TEXT"})
        conn.commit()
    finally:
        conn.close()


def _ensure_columns(conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({_quote(table)})")}
    for name, column_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE {_quote(table)} ADD COLUMN {_quote(name)} {column_type}")


def populate_rekordbox_fixture_db(conn: sqlite3.Connection) -> None:
    now = "2026-01-01 00:00:00"
    _insert(
        conn,
        "djmdContent",
        {
            "ID": "1",
            "UUID": "content-uuid-1",
            "FolderPath": "/Music",
            "FileNameL": "Track One.aiff",
            "Title": "Track One",
            "ArtistName": "Artist One",
            "AlbumName": "Album",
            "GenreName": "House",
            "KeyName": "8A",
            "BPM": 124.0,
            "Length": 300000,
            "rb_local_usn": 1,
            "created_at": now,
            "updated_at": now,
        },
    )
    _insert(conn, "djmdCue", _cue_row(now))
    _insert(
        conn,
        "djmdPlaylist",
        {
            "ID": "10",
            "UUID": "playlist-uuid-10",
            "Seq": 1,
            "Name": "Fixture Playlist",
            "Attribute": 0,
            "ParentID": None,
            "rb_local_usn": 3,
            "created_at": now,
            "updated_at": now,
        },
    )
    _insert(
        conn,
        "djmdSongPlaylist",
        {
            "ID": "11",
            "UUID": "song-playlist-uuid-11",
            "PlaylistID": "10",
            "ContentID": "1",
            "TrackNo": 1,
            "rb_local_usn": 4,
            "created_at": now,
            "updated_at": now,
        },
    )


def _cue_row(now: str) -> dict[str, object]:
    return {
        # Real Rekordbox 7 djmdCue rows use InMsec/OutMsec, Kind, and
        # is_hot_cue/is_memory_cue. Hotcue A is Kind=1, slot Kind-1.
        "ID": "1",
        "UUID": "cue-uuid-1",
        "ContentID": "1",
        "InMsec": 12345,
        "OutMsec": -1,
        "Kind": 1,
        "is_hot_cue": 1,
        "is_memory_cue": 0,
        "Name": "Cue A",
        "Comment": "Cue A",
        "rb_local_usn": 2,
        "created_at": now,
        "updated_at": now,
    }


def _insert(conn: sqlite3.Connection, table: str, values: dict[str, object]) -> None:
    column_info = _column_info(conn, table)
    row = _required_defaults(column_info)
    row.update(values)
    for name, (column_type, notnull, _default) in column_info.items():
        if notnull and row.get(name) is None:
            row[name] = _default_value(name, column_type)
    columns = [column for column in row if column in column_info]
    column_sql = ", ".join(_quote(column) for column in columns)
    placeholder_sql = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {_quote(table)} ({column_sql}) VALUES ({placeholder_sql})",
        tuple(row[column] for column in columns),
    )


def _column_info(conn: sqlite3.Connection, table: str) -> dict[str, tuple[str, bool, object]]:
    return {row[1]: (str(row[2]), bool(row[3]), row[4]) for row in conn.execute(f"PRAGMA table_info({_quote(table)})")}


def _required_defaults(column_info: dict[str, tuple[str, bool, object]]) -> dict[str, object]:
    return {
        name: _default_value(name, column_type)
        for name, (column_type, notnull, default) in column_info.items()
        if notnull and default is None
    }


def _default_value(name: str, column_type: str) -> object:
    if name in {"created_at", "updated_at"}:
        return "2026-01-01 00:00:00"
    if any(token in column_type.upper() for token in ("INT", "SMALLINT", "BIGINT")):
        return 0
    return 0.0 if any(token in column_type.upper() for token in ("FLOAT", "REAL")) else ""


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
