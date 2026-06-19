from __future__ import annotations

import base64
import functools
import sys
import unittest
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

from tests.support.rekordbox_plain_fixture import (
    _ensure_columns,
    build_plain_rekordbox_fixture_db,
    populate_rekordbox_fixture_db,
)

PUBLIC_KEY_BLOB = b"PN_Pq^*N>(JYe*u^8;Yg76HuZ<mR13S?=>)b9;DpoTXV(6ItkU`}8*m6tx_I{Solh_N#dfe{v="
BLOB_KEY = b"657f48f84c437cc1"
F = TypeVar("F", bound=Callable[..., object])


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


def requires_rekordbox_backend(test: F) -> F:
    @functools.wraps(test)
    def wrapper(*args: object, **kwargs: object) -> object:
        reason = rekordbox_backend_skip_reason()
        if reason:
            raise unittest.SkipTest(reason)
        return test(*args, **kwargs)

    return wrapper  # type: ignore[return-value]


def rekordbox_backend_skip_reason() -> str | None:
    if sys.platform == "linux":
        return "pyrekordbox Rekordbox DB backend is unsupported on Linux"
    try:
        _import_pyrekordbox_backend()
    except (ImportError, RuntimeError) as exc:
        return f"pyrekordbox/SQLCipher Rekordbox DB backend is unavailable: {exc}"
    return None


def generate_encrypted_rekordbox_fixture(out_path: Path) -> EncryptedRekordboxFixture:
    reason = rekordbox_backend_skip_reason()
    if reason:
        raise SqlcipherUnavailable(reason)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    plain_copy = out_path.with_suffix(".plain.db")
    if plain_copy.exists():
        plain_copy.unlink()
    build_plain_rekordbox_fixture_db(plain_copy)
    _build_pyrekordbox_encrypted_db(out_path)
    _assert_pyrekordbox_readable(out_path)
    return EncryptedRekordboxFixture(out_path, plain_copy)


def _build_pyrekordbox_encrypted_db(path: Path) -> None:
    try:
        rb_database, Base, create_engine = _import_pyrekordbox_backend()
    except (ImportError, RuntimeError) as exc:
        raise SqlcipherUnavailable(f"pyrekordbox encrypted DB backend is unavailable: {exc}") from exc
    engine = create_engine(
        f"sqlite+pysqlcipher://:{rekordbox_public_sqlcipher_key()}@/{path}?", module=rb_database.sqlite3
    )
    try:
        Base.metadata.create_all(engine)
        conn = engine.raw_connection()
        try:
            _ensure_columns(conn, "djmdCue", {"is_hot_cue": "INTEGER", "is_memory_cue": "INTEGER", "Name": "TEXT"})
            populate_rekordbox_fixture_db(conn)
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        raise SqlcipherUnavailable(f"could not create pyrekordbox-readable encrypted fixture: {exc}") from exc
    finally:
        engine.dispose()


def _assert_pyrekordbox_readable(path: Path) -> None:
    try:
        from pyrekordbox.db6 import database

        from djlib_doctor.rekordbox_db_read import read_rekordbox_master_db
    except (ImportError, RuntimeError) as exc:
        raise SqlcipherUnavailable(f"pyrekordbox encrypted DB backend is unavailable: {exc}") from exc
    original_get_pid = database.get_rekordbox_pid
    database.get_rekordbox_pid = lambda: 0
    try:
        library = read_rekordbox_master_db(path, key=rekordbox_public_sqlcipher_key())
    except Exception as exc:
        raise SqlcipherUnavailable(f"encrypted fixture did not reopen through pyrekordbox: {exc}") from exc
    finally:
        database.get_rekordbox_pid = original_get_pid
    if not library.tracks or library.tracks[0].track_id != "1":
        raise SqlcipherUnavailable("encrypted fixture reopened without the expected fixture track")


def _import_pyrekordbox_backend() -> tuple[object, object, Callable[..., object]]:
    from pyrekordbox.db6 import database as rb_database
    from pyrekordbox.db6.tables import Base
    from sqlalchemy import create_engine

    return rb_database, Base, create_engine
