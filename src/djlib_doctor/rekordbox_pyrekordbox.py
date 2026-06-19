from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable


class PyrekordboxUnavailable(ImportError):
    pass


def open_master_database(
    path: Path, key: str = "", unlock: bool = True, importer: Callable[[], Any] | None = None
) -> Any:
    master_database = _master_database(importer)
    try:
        return master_database(path=path, key=key, unlock=unlock)
    except (OSError, RuntimeError, ValueError) as exc:
        raise unsupported_database_error(path, exc) from exc
    except Exception as exc:
        if is_database_driver_error(exc):
            raise unsupported_database_error(path, exc) from exc
        raise


def close_master_database(db: Any) -> None:
    engine = getattr(db, "engine", None)
    session = getattr(db, "session", None)
    if session is not None:
        session_close = getattr(session, "close", None)
        if callable(session_close):
            session_close()
    close = getattr(db, "close", None)
    if callable(close):
        close()
    dispose = getattr(engine, "dispose", None)
    if callable(dispose):
        dispose()


def _master_database(importer: Callable[[], Any] | None) -> Any:
    if importer is not None:
        try:
            return importer()
        except ImportError as exc:
            raise _unavailable(exc) from exc
    try:
        from pyrekordbox.db6 import Rekordbox6Database
    except ImportError as exc:
        raise _unavailable(exc) from exc
    return Rekordbox6Database


def _unavailable(exc: ImportError) -> PyrekordboxUnavailable:
    error = PyrekordboxUnavailable(
        "Rekordbox SQLCipher backend is unavailable. pyrekordbox and sqlcipher3-wheels are default "
        "djlib-doctor dependencies; reinstall djlib-doctor or verify SQLCipher can import on this system."
    )
    error.__cause__ = exc
    return error


def unsupported_database_error(path: Path, exc: BaseException) -> PyrekordboxUnavailable:
    error = PyrekordboxUnavailable(
        f"pyrekordbox could not unlock or read Rekordbox master.db: {path}. "
        "The database may be key-locked, unsupported by the installed pyrekordbox/SQLCipher backend, "
        f"or not a Rekordbox master.db. Original error: {exc}"
    )
    error.__cause__ = exc
    return error


def is_database_driver_error(exc: Exception) -> bool:
    return isinstance(exc, _database_driver_errors())


def _database_driver_errors() -> tuple[type[BaseException], ...]:
    errors: list[type[BaseException]] = [sqlite3.DatabaseError]
    try:
        from sqlcipher3 import dbapi2 as sqlcipher

        errors.append(sqlcipher.DatabaseError)
    except ImportError:
        pass
    try:
        from sqlalchemy.exc import DatabaseError as SqlalchemyDatabaseError
        from sqlalchemy.exc import OperationalError as SqlalchemyOperationalError

        errors.extend((SqlalchemyDatabaseError, SqlalchemyOperationalError))
    except ImportError:
        pass
    return tuple(dict.fromkeys(errors))
