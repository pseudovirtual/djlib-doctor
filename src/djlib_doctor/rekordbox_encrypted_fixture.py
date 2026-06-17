from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import shutil
import sqlite3
from tempfile import TemporaryDirectory
import zlib

PUBLIC_KEY_BLOB = b"PN_Pq^*N>(JYe*u^8;Yg76HuZ)b9;DpoTXV(6ItkU`}8*m6tx_I{Solh_N#dfe{v="
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
    conn = sqlite3.connect(path)
    try:
        _create_schema(conn)
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
        raise SqlcipherUnavailable("sqlcipher3 is unavailable; install djlib-doctor[rekordbox] to generate encrypted Rekordbox fixtures") from exc
    return sqlcipher


def _create_schema(conn: sqlite3.Connection) -> None:
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
            rb_local_usn INTEGER,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )


def _insert_fixture_rows(conn: sqlite3.Connection) -> None:
    now = "2026-01-01 00:00:00"
    conn.execute(
        "INSERT INTO djmdContent VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "content-uuid-1", "/Music", "Track One.aiff", "Track One", "Artist One", "Album", "House", "8A", 124.0, 300000, 1, now, now),
    )
    conn.execute(
        "INSERT INTO djmdCue VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, "cue-uuid-1", 1, 12345, None, 0, 0, "Cue A", 2, now, now),
    )
