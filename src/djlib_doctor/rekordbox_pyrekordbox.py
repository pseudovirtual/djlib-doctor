from __future__ import annotations

from pathlib import Path
from typing import Callable, Any


class PyrekordboxUnavailable(ImportError):
    pass


def open_master_database(path: Path, key: str = "", unlock: bool = True, importer: Callable[[], Any] | None = None) -> Any:
    master_database = _master_database(importer)
    return master_database(path=path, key=key, unlock=unlock)


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
    error = PyrekordboxUnavailable("Install djlib-doctor[rekordbox] to read or write encrypted Rekordbox master.db files")
    error.__cause__ = exc
    return error
