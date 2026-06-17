from __future__ import annotations

import base64
import shutil
import sqlite3
import zlib
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

PUBLIC_KEY_BLOB = b"PN_Pq^*N>(JYe*u^8;Yg76HuZ<mR13S?=>)b9;DpoTXV(6ItkU`}8*m6tx_I{Solh_N#dfe{v="
BLOB_KEY = b"657f48f84c437cc1"
SQLCIPHER4_PRAGMAS = (
    "PRAGMA cipher_page_size = 4096",
    "PRAGMA kdf_iter = 256000",
    "PRAGMA cipher_hmac_algorithm = HMAC_SHA512",
    "PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512",
)


class SqlcipherUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class EncryptedRekordboxFixture:
    encrypted_db: Path
    plain_db: Path
    schema: str = "sqlcipher4"


def rekordbox_public_sqlcipher_key() -> str:
    data = base64.b85decode(PUBLIC_KEY_BLOB)
    xored = bytes(byte ^ BLOB_KEY[index % len(BLOB_KEY)] for index, byte in enumerate(data))
    return zlib.decompress(xored).decode("utf-8")


def build_plain_rekordbox_fixture_db(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    _create_schema(path)
    conn = sqlite3.connect(path)
    try:
        _insert_fixture_rows(conn)
        conn.commit()
    finally:
        conn.close()
    return path


def generate_encrypted_rekordbox_fixture(out_path: Path) -> EncryptedRekordboxFixture:
    sqlcipher = _sqlcipher()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    plain_copy = out_path.with_suffix(".plain.db")
    if plain_copy.exists():
        plain_copy.unlink()
    with TemporaryDirectory() as tmpdir:
        plain = Path(tmpdir) / "plain-master.db"
        build_plain_rekordbox_fixture_db(plain)
        shutil.copy2(plain, plain_copy)
        _encrypt_plain_db(sqlcipher, plain_copy, out_path)
    return EncryptedRekordboxFixture(out_path, plain_copy)


def _encrypt_plain_db(sqlcipher: object, plain: Path, encrypted: Path) -> None:
    conn = sqlcipher.connect(str(plain))
    try:
        key = rekordbox_public_sqlcipher_key().replace("'", "''")
        target = str(encrypted).replace("'", "''")
        conn.execute(f"ATTACH DATABASE '{target}' AS encrypted KEY '{key}'")
        for pragma in SQLCIPHER4_PRAGMAS:
            conn.execute(pragma.replace("PRAGMA ", "PRAGMA encrypted."))
        conn.execute("SELECT sqlcipher_export('encrypted')")
        conn.execute("DETACH DATABASE encrypted")
    finally:
        conn.close()


def _sqlcipher() -> object:
    try:
        from sqlcipher3 import dbapi2 as sqlcipher
    except ImportError as exc:
        raise SqlcipherUnavailable(
            "sqlcipher3 is unavailable; reinstall djlib-doctor with its default Rekordbox DB dependencies"
        ) from exc
    return sqlcipher


def _create_schema(path: Path) -> None:
    if _create_pyrekordbox_schema(path):
        return
    conn = sqlite3.connect(path)
    try:
        _create_fallback_schema(conn)
        conn.commit()
    finally:
        conn.close()


def _create_pyrekordbox_schema(path: Path) -> bool:
    try:
        from pyrekordbox.db6.tables import Base
        from sqlalchemy import create_engine
    except ImportError:
        return False
    engine = create_engine(f"sqlite:///{path}")
    try:
        Base.metadata.create_all(engine)
    finally:
        engine.dispose()
    return True


def _create_fallback_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE djmdContent(
            ID INTEGER PRIMARY KEY,
            UUID TEXT NOT NULL,
            FolderPath TEXT,
            FileNameL TEXT,
            Title TEXT,
            ArtistName TEXT,
            AlbumName TEXT,
            GenreName TEXT,
            KeyName TEXT,
            BPM REAL,
            Length INTEGER,
            rb_local_usn INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE djmdCue(
            ID INTEGER PRIMARY KEY,
            UUID TEXT NOT NULL,
            ContentID INTEGER,
            InMsec INTEGER,
            OutMsec INTEGER,
            Kind INTEGER,
            HotCue INTEGER,
            Name TEXT,
            Comment TEXT,
            rb_local_usn INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE djmdPlaylist(
            ID INTEGER PRIMARY KEY,
            UUID TEXT,
            Seq INTEGER,
            Name TEXT,
            Attribute INTEGER,
            ParentID INTEGER,
            rb_local_usn INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE djmdSongPlaylist(
            ID INTEGER PRIMARY KEY,
            UUID TEXT,
            PlaylistID INTEGER,
            ContentID INTEGER,
            TrackNo INTEGER,
            rb_local_usn INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )


def _insert_fixture_rows(conn: sqlite3.Connection) -> None:
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
    _insert(
        conn,
        "djmdCue",
        {
            "ID": "1",
            "UUID": "cue-uuid-1",
            "ContentID": "1",
            "InMsec": 12345,
            "OutMsec": None,
            "Kind": 0,
            "HotCue": 0,
            "Name": "Cue A",
            "Comment": "Cue A",
            "rb_local_usn": 2,
            "created_at": now,
            "updated_at": now,
        },
    )
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
    if any(token in column_type.upper() for token in ("FLOAT", "REAL")):
        return 0.0
    return ""


def _quote(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'
