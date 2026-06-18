from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .rekordbox_db_import import build_rekordbox_db_import_operations
from .rekordbox_pyrekordbox import open_master_database
from .safety import all_checks_passed, check_app_processes_closed, check_sqlite_sidecars
from .sqlite_stage import (
    SQLITE_INSTALL_SCHEMA_VERSION,
    SQLITE_STAGE_SCHEMA_VERSION,
    SqliteStage,
    install_sqlite_stage,
    stage_sqlite_operations,
)
from .sqlite_utils import quote_identifier
from .stage_common import install_token, sha256_file


def stage_rekordbox_db_operations(live_db: Path, operations_manifest: Path, stage_dir: Path) -> SqliteStage:
    try:
        return stage_sqlite_operations(
            live_db, operations_manifest, stage_dir, label="rekordbox", artifact_prefix="rekordbox-db"
        )
    except sqlite3.DatabaseError:
        return _stage_encrypted_rekordbox_db_operations(live_db, operations_manifest, stage_dir)


def stage_rekordbox_db_import(live_db: Path, port_manifest: Path, stage_dir: Path) -> SqliteStage:
    operations = build_rekordbox_db_import_operations(
        live_db, port_manifest, stage_dir / "rekordbox-db-import-operations.json"
    )
    return stage_rekordbox_db_operations(live_db, operations, stage_dir)


def install_rekordbox_db_stage(
    stage_dir: Path, live_db: Path, confirm_token: str, process_lines: tuple[str, ...] | list[str] | None = None
) -> dict[str, Any]:
    if process_lines is not None:
        checks = check_app_processes_closed(process_lines, {"rekordbox": ("rekordbox",)})
        if not all_checks_passed(checks):
            raise RuntimeError("Refusing to install while Rekordbox appears to be running")
    return install_sqlite_stage(stage_dir, live_db, confirm_token, label="rekordbox", artifact_prefix="rekordbox-db")


def _stage_encrypted_rekordbox_db_operations(live_db: Path, operations_manifest: Path, stage_dir: Path) -> SqliteStage:
    sidecar_checks = check_sqlite_sidecars(live_db, code="rekordbox_sqlite_sidecar_absent")
    if not all_checks_passed(sidecar_checks):
        raise RuntimeError("Refusing to stage Rekordbox DB operations while sidecars exist")
    stage_dir.mkdir(parents=True, exist_ok=True)
    staged_db = stage_dir / live_db.name
    shutil.copy2(live_db, staged_db)
    operations = tuple(read_json(operations_manifest).get("operations", ()))
    db = open_master_database(staged_db)
    try:
        for operation in operations:
            _apply_pyrekordbox_operation(db, operation)
    finally:
        close = getattr(db, "close", None)
        if callable(close):
            close()
    hashes = {"source_db": sha256_file(live_db), "staged_db": sha256_file(staged_db)}
    token = install_token("INSTALL_SQLITE_STAGE", hashes)
    manifest = {
        "schema_version": SQLITE_STAGE_SCHEMA_VERSION,
        "mode": "staged_rekordbox_db_operations",
        "label": "rekordbox",
        "source_db": str(live_db),
        "operations_manifest": str(operations_manifest),
        "staged_db": str(staged_db),
        "operations": len(operations),
        "hashes": hashes,
        "install_token": token,
    }
    stage_manifest_path = stage_dir / "rekordbox-db-stage-manifest.json"
    write_json(stage_manifest_path, manifest)
    return SqliteStage(stage_dir, stage_manifest_path, staged_db, token)


def _apply_pyrekordbox_operation(db: Any, operation: dict[str, Any]) -> None:
    from sqlalchemy import text

    prepared = _prepare_pyrekordbox_operation(db, operation)
    sql, params = _operation_sql(prepared)
    with db.engine.begin() as conn:
        conn.execute(text(sql), params)


def _prepare_pyrekordbox_operation(db: Any, operation: dict[str, Any]) -> dict[str, Any]:
    columns = _pyrekordbox_columns(db, operation["table"])
    prepared = dict(operation)
    if "values" in prepared:
        values = {column: value for column, value in prepared["values"].items() if column in columns}
        if prepared["operation"] == "insert":
            values = _with_required_defaults(columns, values)
        prepared["values"] = values
    if "where" in prepared:
        prepared["where"] = {column: value for column, value in prepared["where"].items() if column in columns}
    return prepared


def _pyrekordbox_columns(db: Any, table: str) -> dict[str, tuple[str, bool, object]]:
    from sqlalchemy import text

    with db.engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({quote_identifier(table)})")).fetchall()
    return {row[1]: (str(row[2]), bool(row[3]), row[4]) for row in rows}


def _with_required_defaults(columns: dict[str, tuple[str, bool, object]], values: dict[str, Any]) -> dict[str, Any]:
    row = {
        name: _default_pyrekordbox_value(name, column_type)
        for name, (column_type, notnull, default) in columns.items()
        if notnull and default is None
    }
    row.update(values)
    for name, (column_type, notnull, _default) in columns.items():
        if notnull and row.get(name) is None:
            row[name] = _default_pyrekordbox_value(name, column_type)
    return row


def _default_pyrekordbox_value(name: str, column_type: str) -> object:
    if name in {"UUID"}:
        return ""
    if name in {"created_at", "updated_at"}:
        return "2026-01-01 00:00:00"
    if any(token in column_type.upper() for token in ("INT", "SMALLINT", "BIGINT")):
        return 0
    if any(token in column_type.upper() for token in ("FLOAT", "REAL")):
        return 0.0
    return ""


def _operation_sql(operation: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    kind = operation["operation"]
    table = quote_identifier(operation["table"])
    if kind == "update":
        values = operation["values"]
        where = operation["where"]
        assignments = ", ".join(f"{quote_identifier(column)} = :v{index}" for index, column in enumerate(values))
        predicates = " AND ".join(f"{quote_identifier(column)} = :w{index}" for index, column in enumerate(where))
        params = {f"v{index}": value for index, value in enumerate(values.values())}
        params.update({f"w{index}": value for index, value in enumerate(where.values())})
        return f"UPDATE {table} SET {assignments} WHERE {predicates}", params
    if kind == "insert":
        values = operation["values"]
        columns = ", ".join(quote_identifier(column) for column in values)
        placeholders = ", ".join(f":v{index}" for index, _column in enumerate(values))
        params = {f"v{index}": value for index, value in enumerate(values.values())}
        return f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", params
    if kind == "delete":
        where = operation["where"]
        predicates = " AND ".join(f"{quote_identifier(column)} = :w{index}" for index, column in enumerate(where))
        params = {f"w{index}": value for index, value in enumerate(where.values())}
        return f"DELETE FROM {table} WHERE {predicates}", params
    raise ValueError(f"Unsupported Rekordbox DB operation: {kind}")


__all__ = [
    "SQLITE_INSTALL_SCHEMA_VERSION",
    "SQLITE_STAGE_SCHEMA_VERSION",
    "SqliteStage",
    "install_rekordbox_db_stage",
    "stage_rekordbox_db_import",
    "stage_rekordbox_db_operations",
]
