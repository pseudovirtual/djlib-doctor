from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

from .io_utils import read_json, write_json
from .sqlite_utils import quote_identifier, table_columns

IMPORT_SCHEMA_VERSION = "1.0"
CONTENT_TABLE = "djmdContent"
REQUIRED_COLUMNS = ("ID", "FolderPath", "FileNameL", "Title")


def build_rekordbox_db_import_operations(live_db: Path, port_manifest: Path, out_path: Path) -> Path:
    manifest = read_json(port_manifest)
    _require_serato_to_rekordbox_manifest(manifest)
    conn = sqlite3.connect(f"file:{live_db}?mode=ro", uri=True)
    try:
        columns = table_columns(conn, CONTENT_TABLE)
        _require_supported_content_schema(columns)
        operations = _build_operations(conn, columns, manifest.get("tracks", ()))
    finally:
        conn.close()
    write_json(out_path, _operations_manifest(port_manifest, operations))
    return out_path


def _require_serato_to_rekordbox_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("source_platform") != "serato":
        raise ValueError("Port manifest must have source_platform='serato'")
    if manifest.get("target_platform") != "rekordbox_xml":
        raise ValueError("Port manifest must have target_platform='rekordbox_xml'")


def _require_supported_content_schema(columns: tuple[str, ...]) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise ValueError(
            "Unsupported Rekordbox DB schema for import; missing "
            + ", ".join(missing)
            + ". Use port serato-to-rb for a preview until an adapter supports this schema."
        )


def _build_operations(conn: sqlite3.Connection, columns: tuple[str, ...], tracks: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    operations = []
    existing = _existing_paths(conn)
    next_id = _next_content_id(conn)
    for track in tracks:
        values = _content_values(track, columns)
        key = (values["FolderPath"], values["FileNameL"])
        if key in existing:
            operations.append({"operation": "update", "table": CONTENT_TABLE, "values": _update_values(values), "where": {"ID": existing[key]}})
        else:
            values["ID"] = next_id
            operations.append({"operation": "insert", "table": CONTENT_TABLE, "values": values})
            next_id += 1
    return operations


def _existing_paths(conn: sqlite3.Connection) -> dict[tuple[str, str], int]:
    rows = conn.execute(f"SELECT ID, FolderPath, FileNameL FROM {quote_identifier(CONTENT_TABLE)}").fetchall()
    return {(str(folder or ""), str(name or "")): int(content_id) for content_id, folder, name in rows}


def _next_content_id(conn: sqlite3.Connection) -> int:
    value = conn.execute(f"SELECT MAX(ID) FROM {quote_identifier(CONTENT_TABLE)}").fetchone()[0]
    return int(value or 0) + 1


def _content_values(track: dict[str, Any], columns: tuple[str, ...]) -> dict[str, Any]:
    folder, filename = _split_db_path(str(track.get("path") or ""))
    values = {"FolderPath": folder, "FileNameL": filename, "Title": track.get("title") or Path(filename).stem}
    optional = {
        "ArtistName": track.get("artist"),
        "AlbumName": track.get("album"),
        "GenreName": track.get("genre"),
        "KeyName": track.get("key"),
        "BPM": track.get("bpm"),
        "Length": track.get("length_ms"),
    }
    values.update({column: value for column, value in optional.items() if column in columns and value not in (None, "")})
    return values


def _update_values(values: dict[str, Any]) -> dict[str, Any]:
    return {column: value for column, value in values.items() if column != "ID"}


def _split_db_path(path: str) -> tuple[str, str]:
    item = Path(path)
    folder = "" if str(item.parent) == "." else str(item.parent)
    return folder, item.name


def _operations_manifest(port_manifest: Path, operations: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {kind: sum(1 for operation in operations if operation["operation"] == kind) for kind in ("insert", "update")}
    return {
        "schema_version": IMPORT_SCHEMA_VERSION,
        "mode": "rekordbox_db_import_operations",
        "source_port_manifest": str(port_manifest),
        "target_table": CONTENT_TABLE,
        "summary": counts,
        "operations": operations,
    }
