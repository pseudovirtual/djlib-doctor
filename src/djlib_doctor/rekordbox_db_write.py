from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Callable

from . import rekordbox_pyrekordbox
from .sqlite_utils import quote_identifier, require_integrity


def apply_rekordbox_operations(db_path: Path, operations: tuple[dict[str, Any], ...]) -> None:
    def sqlite_apply(conn: sqlite3.Connection) -> None:
        for operation in operations:
            sql, params = _operation_sql(operation, placeholder="?")
            conn.execute(sql, tuple(params.values()))

    def sqlalchemy_apply(conn: Any) -> None:
        for operation in operations:
            sql, params = _operation_sql(_prepare_sqlalchemy_operation(conn, operation))
            conn.execute(_text(sql), params)

    _write_rekordbox_db(db_path, sqlite_apply, sqlalchemy_apply, "staged Rekordbox DB operations")


def update_track_location_and_cues(db_path: Path, track_id: str, target: Path, shift_ms: int, label: str) -> None:
    folder = "" if str(target.parent) == "." else str(target.parent)

    def sqlite_apply(conn: sqlite3.Connection) -> None:
        conn.execute(
            f"UPDATE {quote_identifier('djmdContent')} SET FolderPath = ?, FileNameL = ? WHERE ID = ?",
            (folder, target.name, track_id),
        )
        if shift_ms:
            _shift_sqlite_cues(conn, track_id, shift_ms)

    def sqlalchemy_apply(conn: Any) -> None:
        sql = f"UPDATE {quote_identifier('djmdContent')} SET FolderPath = :folder, FileNameL = :name WHERE ID = :id"
        conn.execute(_text(sql), {"folder": folder, "name": target.name, "id": track_id})
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
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            close()


def _require_sqlalchemy_integrity(conn: Any, phase: str) -> None:
    rows = conn.execute(_text("PRAGMA integrity_check")).fetchall()
    integrity = rows[0][0] if rows else "ok"
    if integrity != "ok":
        raise RuntimeError(f"Rekordbox DB integrity check failed {phase}: {integrity}")


def _shift_sqlite_cues(conn: sqlite3.Connection, track_id: str, shift_ms: int) -> None:
    rows = conn.execute(
        f"SELECT ID, InMsec, OutMsec FROM {quote_identifier('djmdCue')} WHERE ContentID = ?",
        (track_id,),
    ).fetchall()
    for cue_id, in_msec, out_msec in rows:
        _update_cue(conn.execute, cue_id, in_msec, out_msec, shift_ms, qmark=True)


def _shift_sqlalchemy_cues(conn: Any, track_id: str, shift_ms: int) -> None:
    sql = f"SELECT ID, InMsec, OutMsec FROM {quote_identifier('djmdCue')} WHERE ContentID = :id"
    for cue_id, in_msec, out_msec in conn.execute(_text(sql), {"id": track_id}).fetchall():
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
    execute(sql if qmark else _text(sql), params)


def _operation_sql(operation: dict[str, Any], placeholder: str = ":") -> tuple[str, dict[str, Any]]:
    kind = operation["operation"]
    table = quote_identifier(operation["table"])
    if kind in {"update", "insert"}:
        values = operation["values"]
        columns = list(values)
    if kind == "update":
        where = operation["where"]
        assignments = ", ".join(_binding(column, "v", index, placeholder) for index, column in enumerate(columns))
        predicates = " AND ".join(_binding(column, "w", index, placeholder) for index, column in enumerate(where))
        params = {f"v{index}": value for index, value in enumerate(values.values())}
        params.update({f"w{index}": value for index, value in enumerate(where.values())})
        return f"UPDATE {table} SET {assignments} WHERE {predicates}", params
    if kind == "insert":
        column_sql = ", ".join(quote_identifier(column) for column in columns)
        placeholders = ", ".join("?" if placeholder == "?" else f":v{index}" for index, _column in enumerate(columns))
        params = {f"v{index}": value for index, value in enumerate(values.values())}
        return f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})", params
    if kind == "delete":
        where = operation["where"]
        predicates = " AND ".join(_binding(column, "w", index, placeholder) for index, column in enumerate(where))
        params = {f"w{index}": value for index, value in enumerate(where.values())}
        return f"DELETE FROM {table} WHERE {predicates}", params
    raise ValueError(f"Unsupported Rekordbox DB operation: {kind}")


def _prepare_sqlalchemy_operation(conn: Any, operation: dict[str, Any]) -> dict[str, Any]:
    columns = _sqlalchemy_columns(conn, operation["table"])
    prepared = dict(operation)
    if "values" in prepared:
        values = {column: value for column, value in prepared["values"].items() if column in columns}
        if prepared["operation"] == "insert":
            values = _with_required_defaults(columns, values)
        prepared["values"] = values
    if "where" in prepared:
        prepared["where"] = {column: value for column, value in prepared["where"].items() if column in columns}
    return prepared


def _sqlalchemy_columns(conn: Any, table: str) -> dict[str, tuple[str, bool, object]]:
    rows = conn.execute(_text(f"PRAGMA table_info({quote_identifier(table)})")).fetchall()
    return {row[1]: (str(row[2]), bool(row[3]), row[4]) for row in rows}


def _with_required_defaults(columns: dict[str, tuple[str, bool, object]], values: dict[str, Any]) -> dict[str, Any]:
    row = {
        name: _default_value(name, column_type)
        for name, (column_type, notnull, default) in columns.items()
        if notnull and default is None
    }
    row.update(values)
    for name, (column_type, notnull, _default) in columns.items():
        if notnull and row.get(name) is None:
            row[name] = _default_value(name, column_type)
    return row


def _default_value(name: str, column_type: str) -> object:
    upper_type = column_type.upper()
    if name == "UUID":
        return ""
    if name in {"created_at", "updated_at"}:
        return "2026-01-01 00:00:00"
    if any(token in upper_type for token in ("INT", "SMALLINT", "BIGINT")):
        return 0
    return 0.0 if any(token in upper_type for token in ("FLOAT", "REAL")) else ""


def _binding(column: str, prefix: str, index: int, placeholder: str) -> str:
    param = "?" if placeholder == "?" else f":{prefix}{index}"
    return f"{quote_identifier(column)} = {param}"


def _text(sql: str) -> Any:
    try:
        from sqlalchemy import text
    except ImportError:
        return sql

    return text(sql)
