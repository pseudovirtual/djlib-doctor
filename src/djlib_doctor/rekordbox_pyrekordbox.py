from __future__ import annotations

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
        raise _unsupported_database(path, exc) from exc


def _master_database(importer: Callable[[], Any] | None) -> Any:
    if importer is not None:
        try:
            return importer()
        except ImportError as exc:
            raise _unavailable(exc) from exc
    try:
        from pyrekordbox.masterdb import MasterDatabase
    except ImportError as exc:
        raise _unavailable(exc) from exc
    return MasterDatabase


def _unavailable(exc: ImportError) -> PyrekordboxUnavailable:
    error = PyrekordboxUnavailable(
        "Rekordbox SQLCipher backend is unavailable. pyrekordbox and sqlcipher3-wheels are default "
        "djlib-doctor dependencies; reinstall djlib-doctor or verify SQLCipher can import on this system."
    )
    error.__cause__ = exc
    return error


def _unsupported_database(path: Path, exc: BaseException) -> PyrekordboxUnavailable:
    error = PyrekordboxUnavailable(
        f"pyrekordbox could not unlock or read Rekordbox master.db: {path}. "
        "The database may be key-locked, unsupported by the installed pyrekordbox/SQLCipher backend, "
        f"or not a Rekordbox master.db. Original error: {exc}"
    )
    error.__cause__ = exc
    return error
