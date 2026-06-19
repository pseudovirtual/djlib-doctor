from __future__ import annotations

from typing import Any

from .sqlite_utils import quote_identifier


def operation_sql(operation: dict[str, Any], placeholder: str = ":") -> tuple[str, dict[str, Any]]:
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


def prepare_sqlalchemy_operation(conn: Any, operation: dict[str, Any]) -> dict[str, Any]:
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


def sql_text(sql: str) -> Any:
    try:
        from sqlalchemy import text
    except ImportError:
        return sql
    return text(sql)


def _sqlalchemy_columns(conn: Any, table: str) -> dict[str, tuple[str, bool, object]]:
    rows = conn.execute(sql_text(f"PRAGMA table_info({quote_identifier(table)})")).fetchall()
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
