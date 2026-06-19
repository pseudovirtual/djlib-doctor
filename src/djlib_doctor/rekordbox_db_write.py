from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable

from . import rekordbox_pyrekordbox
from .rekordbox_db_sql import operation_sql, prepare_sqlalchemy_operation, sql_text
from .sqlite_utils import quote_identifier, require_integrity


def apply_rekordbox_operations(db_path: Path, operations: tuple[dict[str, Any], ...]) -> None:
    def sqlite_apply(conn: sqlite3.Connection) -> None:
        for operation in operations:
            sql, params = operation_sql(operation, placeholder="?")
            _require_operation_rows_changed(operation, conn.execute(sql, tuple(params.values())))

    def sqlalchemy_apply(conn: Any) -> None:
        for operation in operations:
            sql, params = operation_sql(prepare_sqlalchemy_operation(conn, operation))
            _require_operation_rows_changed(operation, conn.execute(sql_text(sql), params))

    _write_rekordbox_db(db_path, sqlite_apply, sqlalchemy_apply, "staged Rekordbox DB operations")


def update_track_location_and_cues(db_path: Path, track_id: str, target: Path, shift_ms: int, label: str) -> None:
    folder = "" if str(target.parent) == "." else str(target.parent)

    def sqlite_apply(conn: sqlite3.Connection) -> None:
        result = conn.execute(
            f"UPDATE {quote_identifier('djmdContent')} SET FolderPath = ?, FileNameL = ? WHERE ID = ?",
            (folder, target.name, track_id),
        )
        _require_rows_changed(result, "Rekordbox track location update")
        if shift_ms:
            _shift_sqlite_cues(conn, track_id, shift_ms)

    def sqlalchemy_apply(conn: Any) -> None:
        sql = f"UPDATE {quote_identifier('djmdContent')} SET FolderPath = :folder, FileNameL = :name WHERE ID = :id"
        result = conn.execute(sql_text(sql), {"folder": folder, "name": target.name, "id": track_id})
        _require_rows_changed(result, "Rekordbox track location update")
        if shift_ms:
            _shift_sqlalchemy_cues(conn, track_id, shift_ms)

    _write_rekordbox_db(db_path, sqlite_apply, sqlalchemy_apply, label)


def _write_rekordbox_db(db_path: Path, sqlite_apply: Callable, sqlalchemy_apply: Callable, label: str) -> None:
    try:
        _write_plain_sqlite(db_path, sqlite_apply, label)
    except sqlite3.DatabaseError as exc:
        if "file is not a database" not in str(exc).lower():
            raise
        _write_pyrekordbox(db_path, sqlalchemy_apply, label)


def _write_plain_sqlite(db_path: Path, apply: Callable[[sqlite3.Connection], None], label: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        require_integrity(conn, f"before {label}")
        apply(conn)
        require_integrity(conn, f"after {label}")
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _write_pyrekordbox(db_path: Path, apply: Callable[[Any], None], label: str) -> None:
    db = rekordbox_pyrekordbox.open_master_database(db_path)
    try:
        with db.engine.begin() as conn:
            _require_sqlalchemy_integrity(conn, f"before {label}")
            apply(conn)
            _require_sqlalchemy_integrity(conn, f"after {label}")
        _checkpoint_wal(db.engine)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            close()
        dispose = getattr(db.engine, "dispose", None)
        if callable(dispose):
            dispose()


def _checkpoint_wal(engine: Any) -> None:
    with engine.connect() as conn:
        checkpoint_conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        checkpoint_conn.execute(sql_text("PRAGMA wal_checkpoint(TRUNCATE)")).fetchall()


def _require_sqlalchemy_integrity(conn: Any, phase: str) -> None:
    rows = conn.execute(sql_text("PRAGMA integrity_check")).fetchall()
    integrity = rows[0][0] if rows else "ok"
    if integrity != "ok":
        raise RuntimeError(f"Rekordbox DB integrity check failed {phase}: {integrity}")


def _require_operation_rows_changed(operation: dict[str, Any], result: Any) -> None:
    if operation["operation"] == "update":
        _require_rows_changed(result, f"Rekordbox {operation['operation']} on {operation['table']}")


def _require_rows_changed(result: Any, label: str) -> None:
    rowcount = getattr(result, "rowcount", None)
    if rowcount == 0:
        raise RuntimeError(f"{label} matched 0 rows; refusing to silently no-op")


def _shift_sqlite_cues(conn: sqlite3.Connection, track_id: str, shift_ms: int) -> None:
    rows = conn.execute(
        f"SELECT ID, InMsec, OutMsec FROM {quote_identifier('djmdCue')} WHERE ContentID = ?",
        (track_id,),
    ).fetchall()
    for cue_id, in_msec, out_msec in rows:
        _update_cue(conn.execute, cue_id, in_msec, out_msec, shift_ms, qmark=True)


def _shift_sqlalchemy_cues(conn: Any, track_id: str, shift_ms: int) -> None:
    sql = f"SELECT ID, InMsec, OutMsec FROM {quote_identifier('djmdCue')} WHERE ContentID = :id"
    for cue_id, in_msec, out_msec in conn.execute(sql_text(sql), {"id": track_id}).fetchall():
        _update_cue(conn.execute, cue_id, in_msec, out_msec, shift_ms, qmark=False)


def _update_cue(
    execute: Callable[..., Any], cue_id: Any, in_msec: Any, out_msec: Any, shift_ms: int, qmark: bool
) -> None:
    start = max(0, int(in_msec or 0) + shift_ms)
    end = out_msec if out_msec is None or int(out_msec) <= 0 else max(0, int(out_msec) + shift_ms)
    sql = (
        f"UPDATE {quote_identifier('djmdCue')} SET InMsec = ?, OutMsec = ? WHERE ID = ?"
        if qmark
        else (f"UPDATE {quote_identifier('djmdCue')} SET InMsec = :start, OutMsec = :end WHERE ID = :id")
    )
    params = (start, end, cue_id) if qmark else {"start": start, "end": end, "id": cue_id}
    _require_rows_changed(execute(sql if qmark else sql_text(sql), params), "Rekordbox cue update")
