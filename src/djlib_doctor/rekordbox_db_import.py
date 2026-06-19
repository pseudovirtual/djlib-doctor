from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .io_utils import read_json, write_json
from .rekordbox_db_import_pyrekordbox import build_pyrekordbox_import_operations
from .rekordbox_pyrekordbox import PyrekordboxUnavailable
from .sqlite_utils import quote_identifier, table_columns

IMPORT_SCHEMA_VERSION = "1.0"
CONTENT_TABLE = "djmdContent"
CUE_TABLE = "djmdCue"
REQUIRED_COLUMNS = ("ID", "FolderPath", "FileNameL", "Title")
CUE_COLUMNS = ("ID", "ContentID", "InMsec", "OutMsec", "Kind")


def build_rekordbox_db_import_operations(live_db: Path, port_manifest: Path, out_path: Path) -> Path:
    manifest = read_json(port_manifest)
    _require_serato_to_rekordbox_manifest(manifest)
    conn = sqlite3.connect(f"file:{live_db}?mode=ro", uri=True)
    try:
        try:
            columns = table_columns(conn, CONTENT_TABLE)
            _require_supported_content_schema(columns)
            cue_columns = table_columns(conn, CUE_TABLE)
            operations = _build_operations(conn, columns, cue_columns, manifest.get("tracks", ()))
        except sqlite3.DatabaseError:
            try:
                operations = build_pyrekordbox_import_operations(
                    live_db, manifest.get("tracks", ()), CONTENT_TABLE, CUE_TABLE
                )
            except PyrekordboxUnavailable as rb_exc:
                raise ValueError(_unsupported_database_message(live_db)) from rb_exc
    finally:
        conn.close()
    write_json(out_path, _operations_manifest(port_manifest, operations))
    return out_path


def _require_serato_to_rekordbox_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("source_platform") != "serato":
        raise ValueError("Port manifest must have source_platform='serato'")
    if manifest.get("target_platform") != "rekordbox_xml":
        raise ValueError("Port manifest must have target_platform='rekordbox_xml'")


def _unsupported_database_message(path: Path) -> str:
    return (
        f"Unsupported Rekordbox DB format for import: {path}. "
        "This command supports plain SQLite master.db fixtures/schemas with djmdContent "
        "and optional djmdCue tables. encrypted SQLCipher Rekordbox databases require "
        "a pyrekordbox/SQLCipher backend that can unlock and map the DB."
    )


def _require_supported_content_schema(columns: tuple[str, ...]) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in columns]
    if missing:
        raise ValueError(
            "Unsupported Rekordbox DB schema for import; missing "
            + ", ".join(missing)
            + ". Use port serato-to-rb for a preview until an adapter supports this schema."
        )


def _build_operations(
    conn: sqlite3.Connection, columns: tuple[str, ...], cue_columns: tuple[str, ...], tracks: tuple[dict[str, Any], ...]
) -> list[dict[str, Any]]:
    operations = []
    existing = _existing_paths(conn)
    next_id = _next_content_id(conn)
    next_cue_id = _next_id(conn, CUE_TABLE) if cue_columns else 1
    for track in tracks:
        values = _content_values(track, columns)
        key = (values["FolderPath"], values["FileNameL"])
        if key in existing:
            content_id = existing[key]
            operations.append(
                {
                    "operation": "update",
                    "table": CONTENT_TABLE,
                    "values": _update_values(values),
                    "where": {"ID": existing[key]},
                }
            )
        else:
            content_id = next_id
            values["ID"] = next_id
            operations.append({"operation": "insert", "table": CONTENT_TABLE, "values": values})
            next_id += 1
        cue_ops, next_cue_id = _cue_operations(track, cue_columns, content_id, next_cue_id)
        operations.extend(cue_ops)
    return operations


def _existing_paths(conn: sqlite3.Connection) -> dict[tuple[str, str], int]:
    rows = conn.execute(f"SELECT ID, FolderPath, FileNameL FROM {quote_identifier(CONTENT_TABLE)}").fetchall()
    return {(str(folder or ""), str(name or "")): int(content_id) for content_id, folder, name in rows}


def _next_content_id(conn: sqlite3.Connection) -> int:
    return _next_id(conn, CONTENT_TABLE)


def _next_id(conn: sqlite3.Connection, table: str) -> int:
    value = conn.execute(f"SELECT MAX(ID) FROM {quote_identifier(table)}").fetchone()[0]
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
    values.update(
        {column: value for column, value in optional.items() if column in columns and value not in (None, "")}
    )
    return values


def _update_values(values: dict[str, Any]) -> dict[str, Any]:
    return {column: value for column, value in values.items() if column != "ID"}


def _split_db_path(path: str) -> tuple[str, str]:
    item = Path(path)
    folder = "" if str(item.parent) == "." else str(item.parent)
    return folder, item.name


def _cue_operations(
    track: dict[str, Any], columns: tuple[str, ...], content_id: int, next_id: int
) -> tuple[list[dict[str, Any]], int]:
    cues = tuple(track.get("cues") or ())
    if not cues:
        return [], next_id
    _require_supported_cue_schema(columns)
    operations = [{"operation": "delete", "table": CUE_TABLE, "where": {"ContentID": content_id}}]
    for cue in cues:
        values = {column: value for column, value in _cue_values(cue, content_id, next_id).items() if column in columns}
        operations.append({"operation": "insert", "table": CUE_TABLE, "values": values})
        next_id += 1
    return operations, next_id


def _require_supported_cue_schema(columns: tuple[str, ...]) -> None:
    missing = [column for column in CUE_COLUMNS if column not in columns]
    if missing:
        raise ValueError("Unsupported Rekordbox cue table for import; missing " + ", ".join(missing))


def _cue_values(cue: dict[str, Any], content_id: int, cue_id: int) -> dict[str, Any]:
    values = {
        "ID": cue_id,
        "ContentID": content_id,
        "InMsec": int(cue["start_ms"]),
        "OutMsec": -1 if cue.get("end_ms") is None else int(cue["end_ms"]),
        "Kind": _cue_kind(cue),
    }
    values.update(_optional_cue_values(cue))
    return values


def _cue_kind(cue: dict[str, Any]) -> int:
    slot = cue.get("slot")
    return int(slot) + 1 if slot is not None else 0


def _optional_cue_values(cue: dict[str, Any]) -> dict[str, Any]:
    slot = cue.get("slot")
    is_hot = slot is not None
    return {
        "is_hot_cue": is_hot,
        "is_memory_cue": not is_hot,
        "Name": str(cue.get("label") or ""),
        "Comment": str(cue.get("label") or ""),
    }


def _operations_manifest(port_manifest: Path, operations: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        kind: sum(1 for operation in operations if operation["operation"] == kind) for kind in ("insert", "update")
    }
    return {
        "schema_version": IMPORT_SCHEMA_VERSION,
        "mode": "rekordbox_db_import_operations",
        "source_port_manifest": str(port_manifest),
        "target_table": CONTENT_TABLE,
        "summary": counts,
        "operations": operations,
    }
