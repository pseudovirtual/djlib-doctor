from __future__ import annotations

import sqlite3
from typing import Any


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def table_columns(conn: sqlite3.Connection, table: str) -> tuple[str, ...]:
    return tuple(row[1] for row in conn.execute(f"PRAGMA table_info({quote_identifier(table)})"))


def require_integrity(conn: sqlite3.Connection, phase: str, label: str = "SQLite") -> None:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"{label} integrity check failed {phase}: {integrity}")


def require_columns(conn: sqlite3.Connection, table: str, columns: tuple[str, ...], label: str = "SQLite") -> None:
    existing = set(table_columns(conn, table))
    missing = [column for column in columns if column not in existing]
    if missing:
        raise ValueError(f"{label} table {table!r} is missing required columns: {', '.join(missing)}")


def dynamic_insert(conn: sqlite3.Connection, table: str, values: dict[str, Any]) -> int:
    columns = tuple(column for column in values if column in table_columns(conn, table))
    quoted_columns = ", ".join(quote_identifier(column) for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    cursor = conn.execute(
        f"INSERT INTO {quote_identifier(table)} ({quoted_columns}) VALUES ({placeholders})",
        tuple(values[column] for column in columns),
    )
    return int(cursor.lastrowid)


def dynamic_update(
    conn: sqlite3.Connection,
    table: str,
    values: dict[str, Any],
    where_sql: str,
    where_args: tuple[Any, ...],
) -> None:
    columns = tuple(column for column in values if column in table_columns(conn, table))
    if columns:
        assignments = ", ".join(f"{quote_identifier(column)} = ?" for column in columns)
        conn.execute(
            f"UPDATE {quote_identifier(table)} SET {assignments} WHERE {where_sql}",
            tuple(values[column] for column in columns) + where_args,
        )
